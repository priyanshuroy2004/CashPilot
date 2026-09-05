"""
Forward Settlement Forecast Engine — Phase 4

Generates expected settlement date projections for captured payments
that have not yet been settled, across four time horizons: 1, 3, 7, 14 days.

ARCHITECTURAL RULE:
  Forecast amounts are labelled EXPECTED and must NEVER be combined with
  actual bank credits or reported as "received" funds.

Gateway Settlement Lag Estimates (business days):
  Razorpay : 2 days
  PayU     : 3 days
  Stripe   : 5 days
  Default  : 3 days

These lags are used to set expected_settlement_date.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import Payment, Settlement, SettlementLine, SettlementForecast, AuditTrailEvent
from app.services.audit.trail import log_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gateway settlement lag table (calendar days, conservative estimates)
# ---------------------------------------------------------------------------
GATEWAY_LAG_DAYS: Dict[str, int] = {
    "razorpay": 2,
    "payu": 3,
    "cashfree": 3,
    "stripe": 5,
    "paypal": 4,
    "default": 3,
}

FORECAST_HORIZONS = [1, 3, 7, 14]


def _get_gateway_lag(gateway: str | None) -> int:
    """Return estimated settlement lag in calendar days for a gateway."""
    if not gateway:
        return GATEWAY_LAG_DAYS["default"]
    return GATEWAY_LAG_DAYS.get(gateway.lower().strip(), GATEWAY_LAG_DAYS["default"])


def _already_settled(db: Session, payment_id: str) -> bool:
    """Return True if payment_id exists in settlement_lines (meaning it's settled)."""
    return db.query(SettlementLine).filter(
        SettlementLine.payment_id == payment_id
    ).first() is not None


def run_forecast_engine(db: Session) -> Dict[str, Any]:
    """
    Run the forward settlement forecast engine.

    Steps:
    1. Find all captured payments not yet in settlement_lines.
    2. For each unsettled payment, compute expected settlement dates
       for each horizon day (1, 3, 7, 14).
    3. Delete existing PENDING forecasts for the same payment_id to avoid
       duplicates, then insert fresh forecast records.
    4. Write ENGINE_RUN audit event.

    Returns a summary dict usable by the API response.
    """
    as_of = datetime.utcnow()

    # ── Step 1: Find captured, unsettled payments ──────────────────────────
    # Payments with status = 'captured' that are NOT in settlement_lines
    settled_payment_ids = db.query(SettlementLine.payment_id).distinct().subquery()

    unsettled_payments = db.query(Payment).filter(
        Payment.status == "captured",
        ~Payment.payment_id.in_(db.query(settled_payment_ids)),
    ).all()

    logger.info(f"Forecast engine: {len(unsettled_payments)} unsettled captured payments found.")

    # ── Step 2: Delete existing forecasts for unsettled payments to refresh ──
    if unsettled_payments:
        unsettled_ids = [p.payment_id for p in unsettled_payments]
        db.query(SettlementForecast).filter(
            SettlementForecast.payment_id.in_(unsettled_ids)
        ).delete(synchronize_session=False)

    # ── Step 3: Create forecast records ───────────────────────────────────
    new_forecasts: List[SettlementForecast] = []
    horizon_totals: Dict[int, Dict[str, Any]] = {h: {"count": 0, "amount_paise": 0} for h in FORECAST_HORIZONS}

    for payment in unsettled_payments:
        captured_at = payment.payment_captured_at or payment.created_at or as_of
        gateway = payment.payment_method  # e.g. "razorpay", "card", etc.
        lag_days = _get_gateway_lag(gateway)

        # Determine basis for the forecast
        if payment.payment_captured_at:
            basis = "PAYMENT_CAPTURE_DATE"
        else:
            basis = "PAYMENT_CAPTURE_DATE"

        for horizon in FORECAST_HORIZONS:
            # Expected settlement date = capture time + gateway lag
            # The horizon represents "will this settle within N days from NOW?"
            expected_date = captured_at + timedelta(days=lag_days)

            # Determine status relative to now
            if expected_date < as_of:
                status = "OVERDUE"
            else:
                status = "PENDING"

            forecast = SettlementForecast(
                forecast_id=f"FCST-{uuid.uuid4().hex[:12].upper()}",
                payment_id=payment.payment_id,
                order_id=payment.order_id,
                settlement_id=None,
                expected_amount_paise=payment.amount,
                horizon_days=horizon,
                expected_settlement_date=expected_date,
                basis=basis,
                status=status,
                payment_captured_at=payment.payment_captured_at,
                gateway=gateway,
            )
            new_forecasts.append(forecast)

            # Accumulate summary for this horizon
            if expected_date <= as_of + timedelta(days=horizon):
                horizon_totals[horizon]["count"] += 1
                horizon_totals[horizon]["amount_paise"] += payment.amount

    db.bulk_save_objects(new_forecasts)

    # ── Step 4: Mark SETTLED for payments now in settlement_lines ─────────
    settled_now = db.query(SettlementLine.payment_id).distinct().all()
    settled_ids = [r[0] for r in settled_now]
    if settled_ids:
        db.query(SettlementForecast).filter(
            SettlementForecast.payment_id.in_(settled_ids),
            SettlementForecast.status.in_(["PENDING", "OVERDUE"]),
        ).update({"status": "SETTLED"}, synchronize_session=False)

    # ── Step 5: Audit event ────────────────────────────────────────────────
    log_event(
        db=db,
        entity_type="SYSTEM",
        entity_id="FORECAST_ENGINE",
        event_type="ENGINE_RUN",
        actor="system",
        to_value={
            "unsettled_payments": len(unsettled_payments),
            "forecasts_created": len(new_forecasts),
            "horizons": {str(h): horizon_totals[h] for h in FORECAST_HORIZONS},
        },
        notes=f"Forecast engine run at {as_of.isoformat()}",
    )

    db.commit()

    # ── Build summary response ─────────────────────────────────────────────
    def _inr(paise: int) -> str:
        return f"₹{paise / 100:,.2f}"

    return {
        "success": True,
        "message": f"Forecast engine complete. {len(unsettled_payments)} unsettled payments projected.",
        "unsettled_payments_count": len(unsettled_payments),
        "forecasts_created": len(new_forecasts),
        "horizon_summary": {
            str(h): {
                "horizon_days": h,
                "payment_count": horizon_totals[h]["count"],
                "expected_amount_paise": horizon_totals[h]["amount_paise"],
                "expected_amount_inr": _inr(horizon_totals[h]["amount_paise"]),
            }
            for h in FORECAST_HORIZONS
        },
    }
