"""
Forecast & Cash-Gap Alerts API — Phase 4

Endpoints:
  POST /api/forecast/run        — Run forecast engine + gap detector
  GET  /api/forecast/summary    — KPI summary by horizon (EXPECTED only)
  GET  /api/forecast/upcoming   — Paginated pending/overdue forecasts
  GET  /api/forecast/alerts     — Paginated cash-gap alerts
  GET  /api/forecast/alerts/summary — Alert KPIs
  PATCH /api/forecast/alerts/{alert_id}/acknowledge — Acknowledge alert

ARCHITECTURAL NOTE:
  Forecast amounts are always labelled EXPECTED and MUST NOT be
  combined with actual bank credit amounts in any display or calculation.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import SettlementForecast, CashGapAlert
from app.schemas.forecast import (
    ForecastRunResponse,
    ForecastSummary,
    HorizonSummary,
    PaginatedForecasts,
    ForecastRecord,
    PaginatedAlerts,
    CashGapAlertResponse,
    AlertsSummary,
    AlertAcknowledgeRequest,
)
from app.services.forecast import run_forecast_engine, run_gap_detection
from app.services.audit.trail import log_event

router = APIRouter(prefix="/api/forecast", tags=["Forecast & Alerts"])


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _inr(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"


def _to_forecast_record(f: SettlementForecast) -> ForecastRecord:
    return ForecastRecord(
        id=f.id,
        forecast_id=f.forecast_id,
        payment_id=f.payment_id,
        order_id=f.order_id,
        settlement_id=f.settlement_id,
        expected_amount_paise=f.expected_amount_paise,
        expected_amount_inr=_inr(f.expected_amount_paise),
        horizon_days=f.horizon_days,
        expected_settlement_date=_fmt_dt(f.expected_settlement_date) or "",
        basis=f.basis,
        status=f.status,
        payment_captured_at=_fmt_dt(f.payment_captured_at),
        gateway=f.gateway,
        created_at=_fmt_dt(f.created_at) or "",
    )


def _to_alert_response(a: CashGapAlert) -> CashGapAlertResponse:
    return CashGapAlertResponse(
        id=a.id,
        alert_id=a.alert_id,
        alert_type=a.alert_type,
        payment_id=a.payment_id,
        settlement_id=a.settlement_id,
        order_id=a.order_id,
        expected_date=_fmt_dt(a.expected_date),
        actual_date=_fmt_dt(a.actual_date),
        gap_days=a.gap_days,
        gap_amount_paise=a.gap_amount_paise,
        gap_amount_inr=_inr(a.gap_amount_paise),
        severity=a.severity,
        status=a.status,
        notes=a.notes,
        created_at=_fmt_dt(a.created_at) or "",
        updated_at=_fmt_dt(a.updated_at) or "",
    )


# ---------------------------------------------------------------------------
# Run Forecast Engine + Gap Detector
# ---------------------------------------------------------------------------

@router.post("/run", response_model=ForecastRunResponse, summary="Run forecast engine and cash-gap detector")
def run_forecast(db: Session = Depends(get_db)):
    """
    Run the forward settlement forecast engine followed by the cash-gap detector.

    1. Projects expected settlement dates for all captured, unsettled payments.
    2. Identifies cash gaps (overdue forecasts, settlements without bank match).
    3. Writes an ENGINE_RUN audit trail event.

    NOTE: Returned amounts are EXPECTED projections, not actual bank receipts.
    """
    try:
        forecast_result = run_forecast_engine(db)
        gap_result = run_gap_detection(db)
        return ForecastRunResponse(
            success=True,
            message=forecast_result["message"],
            unsettled_payments_count=forecast_result["unsettled_payments_count"],
            forecasts_created=forecast_result["forecasts_created"],
            horizon_summary=forecast_result["horizon_summary"],
            gap_detection=gap_result,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Forecast engine failed: {str(exc)}")


# ---------------------------------------------------------------------------
# Forecast Summary KPIs
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=ForecastSummary, summary="Forecast KPI summary by horizon")
def get_forecast_summary(db: Session = Depends(get_db)):
    """
    Returns expected cash inflow projections split by 1/3/7/14 day horizons.

    IMPORTANT: These are EXPECTED projections only — they represent payments
    captured but not yet settled. They are NOT actual bank credits.
    """
    from sqlalchemy import func, and_
    from datetime import timedelta

    now = datetime.utcnow()

    def _horizon_summary(days: int) -> HorizonSummary:
        cutoff = now + timedelta(days=days)
        rows = db.query(SettlementForecast).filter(
            SettlementForecast.horizon_days == days,
            SettlementForecast.status.in_(["PENDING", "OVERDUE"]),
            SettlementForecast.expected_settlement_date <= cutoff,
        ).all()
        count = len(rows)
        total_paise = sum(r.expected_amount_paise for r in rows)
        return HorizonSummary(
            horizon_days=days,
            payment_count=count,
            expected_amount_paise=total_paise,
            expected_amount_inr=_inr(total_paise),
        )

    overdue_rows = db.query(SettlementForecast).filter(
        SettlementForecast.status == "OVERDUE",
        SettlementForecast.horizon_days == 1,
    ).all()
    overdue_paise = sum(r.expected_amount_paise for r in overdue_rows)

    pending_rows = db.query(SettlementForecast).filter(
        SettlementForecast.status == "PENDING",
        SettlementForecast.horizon_days == 1,
    ).all()
    pending_paise = sum(r.expected_amount_paise for r in pending_rows)

    return ForecastSummary(
        horizon_1_day=_horizon_summary(1),
        horizon_3_days=_horizon_summary(3),
        horizon_7_days=_horizon_summary(7),
        horizon_14_days=_horizon_summary(14),
        total_overdue_count=len(overdue_rows),
        total_overdue_paise=overdue_paise,
        total_overdue_inr=_inr(overdue_paise),
        pending_count=len(pending_rows),
        pending_paise=pending_paise,
        pending_inr=_inr(pending_paise),
    )


# ---------------------------------------------------------------------------
# Upcoming / Pending Forecasts
# ---------------------------------------------------------------------------

@router.get("/upcoming", response_model=PaginatedForecasts, summary="Paginated pending/overdue forecasts")
def get_upcoming_forecasts(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, OVERDUE, SETTLED"),
    horizon_days: Optional[int] = Query(None, description="Filter by horizon: 1, 3, 7, 14"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns paginated list of settlement forecast records sorted by expected settlement date.
    Defaults to PENDING and OVERDUE records only.
    """
    query = db.query(SettlementForecast)
    if status:
        query = query.filter(SettlementForecast.status == status.upper().strip())
    else:
        query = query.filter(SettlementForecast.status.in_(["PENDING", "OVERDUE"]))
    if horizon_days:
        query = query.filter(SettlementForecast.horizon_days == horizon_days)
    else:
        # Default: show horizon_days == 1 (shortest window gives one record per payment)
        query = query.filter(SettlementForecast.horizon_days == 1)

    total = query.count()
    items = (
        query.order_by(SettlementForecast.expected_settlement_date.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedForecasts(
        total=total,
        items=[_to_forecast_record(f) for f in items],
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Cash Gap Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts/summary", response_model=AlertsSummary, summary="Cash gap alert KPI summary")
def get_alerts_summary(db: Session = Depends(get_db)):
    """Returns KPI counts and total risk for all open cash gap alerts."""
    open_alerts = db.query(CashGapAlert).filter(CashGapAlert.status.in_(["OPEN", "ACKNOWLEDGED"])).all()
    by_type: dict = {}
    critical = high = medium = low = 0
    total_risk = 0
    for a in open_alerts:
        by_type[a.alert_type] = by_type.get(a.alert_type, 0) + 1
        total_risk += a.gap_amount_paise
        sev = (a.severity or "").upper()
        if sev == "CRITICAL":
            critical += 1
        elif sev == "HIGH":
            high += 1
        elif sev == "MEDIUM":
            medium += 1
        else:
            low += 1

    return AlertsSummary(
        total_open=len(open_alerts),
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        total_risk_paise=total_risk,
        total_risk_inr=_inr(total_risk),
        by_type=by_type,
    )


@router.get("/alerts", response_model=PaginatedAlerts, summary="Paginated cash-gap alerts")
def get_alerts(
    status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED"),
    severity: Optional[str] = Query(None, description="CRITICAL | HIGH | MEDIUM | LOW"),
    alert_type: Optional[str] = Query(None, description="OVERDUE_SETTLEMENT | RISK_GAP | SETTLEMENT_DELAY"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Returns paginated cash gap alert records, sorted by severity then created_at desc."""
    query = db.query(CashGapAlert)
    if status:
        query = query.filter(CashGapAlert.status == status.upper().strip())
    else:
        query = query.filter(CashGapAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))
    if severity:
        query = query.filter(CashGapAlert.severity == severity.upper().strip())
    if alert_type:
        query = query.filter(CashGapAlert.alert_type == alert_type.upper().strip())

    total = query.count()
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    items = (
        query.order_by(CashGapAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Sort by severity client-side within this page
    items.sort(key=lambda a: sev_order.get((a.severity or "LOW").upper(), 4))

    return PaginatedAlerts(
        total=total,
        items=[_to_alert_response(a) for a in items],
        limit=limit,
        offset=offset,
    )


@router.patch("/alerts/{alert_id}/acknowledge", response_model=CashGapAlertResponse, summary="Acknowledge a cash gap alert")
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
):
    """
    Mark an alert as ACKNOWLEDGED. Writes an immutable audit trail event.
    RESOLVED alerts cannot be acknowledged again.
    """
    alert = db.query(CashGapAlert).filter(CashGapAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    if alert.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Alert is already RESOLVED.")

    old_status = alert.status
    alert.status = "ACKNOWLEDGED"
    alert.notes = payload.notes or alert.notes
    alert.updated_at = datetime.utcnow()

    log_event(
        db=db,
        entity_type="CASH_GAP_ALERT",
        entity_id=alert.alert_id,
        event_type="ACKNOWLEDGEMENT",
        actor="user",
        from_value={"status": old_status},
        to_value={"status": "ACKNOWLEDGED"},
        notes=payload.notes,
    )

    db.commit()
    db.refresh(alert)
    return _to_alert_response(alert)
