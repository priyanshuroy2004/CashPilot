"""
Cash Gap Detector — Phase 4

Detects gaps between expected and actual settlement timing.
Writes CashGapAlert records for payments overdue for settlement.

Gap Severity Scale:
  CRITICAL : gap > 7 days
  HIGH     : gap 4-7 days
  MEDIUM   : gap 2-3 days
  LOW      : gap <= 1 day
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import (
    SettlementForecast,
    CashGapAlert,
    Settlement,
    BankTransaction,
)
from app.services.audit.trail import log_event

logger = logging.getLogger(__name__)


def _gap_severity(gap_days: int) -> str:
    if gap_days > 7:
        return "CRITICAL"
    elif gap_days > 3:
        return "HIGH"
    elif gap_days > 1:
        return "MEDIUM"
    else:
        return "LOW"


def run_gap_detection(db: Session) -> Dict[str, Any]:
    """
    Scan for cash gaps and create/update CashGapAlert records.

    Detects two types of gaps:
    1. OVERDUE_SETTLEMENT — SettlementForecast records with status=OVERDUE
    2. RISK_GAP — Settlements with status='settled' but no matched bank
                  transaction within 72 hours

    Returns a summary dict for the API response.
    """
    as_of = datetime.utcnow()
    created_count = 0
    updated_count = 0

    # ── Type 1: OVERDUE_SETTLEMENT gaps ──────────────────────────────────
    # Forecasts for horizon_days=1 (the shortest window) that are OVERDUE
    overdue_forecasts = (
        db.query(SettlementForecast)
        .filter(
            SettlementForecast.status == "OVERDUE",
            SettlementForecast.horizon_days == 1,
        )
        .all()
    )

    seen_payments = set()
    for forecast in overdue_forecasts:
        if forecast.payment_id in seen_payments:
            continue
        seen_payments.add(forecast.payment_id)

        gap_days = max(0, (as_of - forecast.expected_settlement_date).days)
        severity = _gap_severity(gap_days)

        # Check if alert already exists for this payment
        existing = db.query(CashGapAlert).filter(
            and_(
                CashGapAlert.payment_id == forecast.payment_id,
                CashGapAlert.alert_type == "OVERDUE_SETTLEMENT",
                CashGapAlert.status != "RESOLVED",
            )
        ).first()

        if existing:
            # Update severity and gap_days if the gap has grown
            if existing.gap_days != gap_days:
                existing.gap_days = gap_days
                existing.severity = severity
                existing.updated_at = as_of
                updated_count += 1
        else:
            alert = CashGapAlert(
                alert_id=f"GAP-{uuid.uuid4().hex[:12].upper()}",
                alert_type="OVERDUE_SETTLEMENT",
                payment_id=forecast.payment_id,
                settlement_id=forecast.settlement_id,
                order_id=forecast.order_id,
                expected_date=forecast.expected_settlement_date,
                actual_date=None,
                gap_days=gap_days,
                gap_amount_paise=forecast.expected_amount_paise,
                severity=severity,
                status="OPEN",
            )
            db.add(alert)
            db.flush()
            log_event(
                db=db,
                entity_type="CASH_GAP_ALERT",
                entity_id=alert.alert_id,
                event_type="DETECTION",
                actor="system",
                to_value={
                    "alert_type": "OVERDUE_SETTLEMENT",
                    "payment_id": forecast.payment_id,
                    "gap_days": gap_days,
                    "severity": severity,
                    "amount_paise": forecast.expected_amount_paise,
                },
            )
            created_count += 1

    # ── Type 2: RISK_GAP — settled but no bank match ─────────────────────
    # Settlements created > 72h ago with no matching bank transaction
    cutoff = as_of - timedelta(hours=72)
    settlements_no_bank = (
        db.query(Settlement)
        .filter(
            Settlement.status == "settled",
            Settlement.settlement_date < cutoff,
        )
        .all()
    )

    for settlement in settlements_no_bank:
        # Check for matching bank transaction by UTR
        bank_match = None
        if settlement.settlement_utr:
            bank_match = db.query(BankTransaction).filter(
                BankTransaction.utr == settlement.settlement_utr,
                BankTransaction.direction == "CREDIT",
            ).first()

        if bank_match:
            # Resolve any open RISK_GAP alert for this settlement
            db.query(CashGapAlert).filter(
                CashGapAlert.settlement_id == settlement.settlement_id,
                CashGapAlert.alert_type == "RISK_GAP",
                CashGapAlert.status != "RESOLVED",
            ).update({"status": "RESOLVED", "actual_date": as_of}, synchronize_session=False)
            continue

        gap_days = max(0, (as_of - settlement.settlement_date).days)
        severity = _gap_severity(gap_days)

        existing = db.query(CashGapAlert).filter(
            and_(
                CashGapAlert.settlement_id == settlement.settlement_id,
                CashGapAlert.alert_type == "RISK_GAP",
                CashGapAlert.status != "RESOLVED",
            )
        ).first()

        if existing:
            if existing.gap_days != gap_days:
                existing.gap_days = gap_days
                existing.severity = severity
                existing.updated_at = as_of
                updated_count += 1
        else:
            alert = CashGapAlert(
                alert_id=f"GAP-{uuid.uuid4().hex[:12].upper()}",
                alert_type="RISK_GAP",
                payment_id=None,
                settlement_id=settlement.settlement_id,
                order_id=None,
                expected_date=settlement.settlement_date + timedelta(hours=48),
                actual_date=None,
                gap_days=gap_days,
                gap_amount_paise=settlement.net_amount,
                severity=severity,
                status="OPEN",
            )
            db.add(alert)
            log_event(
                db=db,
                entity_type="CASH_GAP_ALERT",
                entity_id=alert.alert_id,
                event_type="DETECTION",
                actor="system",
                to_value={
                    "alert_type": "RISK_GAP",
                    "settlement_id": settlement.settlement_id,
                    "gap_days": gap_days,
                    "severity": severity,
                },
            )
            created_count += 1

    # ── Resolve alerts for payments that are now settled ──────────────────
    settled_payment_ids_subq = (
        db.query(SettlementForecast.payment_id)
        .filter(SettlementForecast.status == "SETTLED")
        .distinct()
        .subquery()
    )
    resolved = (
        db.query(CashGapAlert)
        .filter(
            CashGapAlert.alert_type == "OVERDUE_SETTLEMENT",
            CashGapAlert.status != "RESOLVED",
            CashGapAlert.payment_id.in_(db.query(settled_payment_ids_subq)),
        )
        .all()
    )
    for alert in resolved:
        alert.status = "RESOLVED"
        alert.actual_date = as_of
        updated_count += 1

    db.commit()

    total_alerts = db.query(CashGapAlert).filter(CashGapAlert.status == "OPEN").count()
    total_risk_paise = sum(
        a.gap_amount_paise
        for a in db.query(CashGapAlert).filter(CashGapAlert.status == "OPEN").all()
    )

    return {
        "alerts_created": created_count,
        "alerts_updated": updated_count,
        "total_open_alerts": total_alerts,
        "total_risk_paise": total_risk_paise,
        "total_risk_inr": f"₹{total_risk_paise / 100:,.2f}",
    }
