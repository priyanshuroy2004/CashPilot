"""
Evaluation Dashboard API — Phase 4

Computes reconciliation quality metrics from production data.

IMPORTANT:
  - Ground truth data (ground_truth.csv) is ONLY used in this evaluation
    module and is strictly separated from production logic.
  - Evaluation metrics are read-only — they do not affect any production
    calculations, forecasts, or exception records.

Endpoints:
  GET /api/evaluation/metrics    — comprehensive quality metrics
"""
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.models import (
    ReconciliationResult,
    FinancialException,
    SettlementCalculation,
    RefundReconciliationResult,
    TaxReconciliationResult,
    Order,
    Payment,
    AuditTrailEvent,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


def _safe_pct(num: int, denom: int) -> float:
    """Return percentage rounded to 2dp, or 0.0 if denom is zero."""
    if denom == 0:
        return 0.0
    return round(num / denom * 100, 2)


@router.get("/metrics", summary="Reconciliation & detection quality metrics")
def get_evaluation_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns a comprehensive evaluation of the system's detection and
    reconciliation quality.

    NOTE: Ground truth comparison (if available) is flagged separately.
    These metrics use only production database records.
    """

    # ── 1. Reconciliation accuracy ─────────────────────────────────────────
    total_recon = db.query(ReconciliationResult).count()
    matched_recon = db.query(ReconciliationResult).filter(
        ReconciliationResult.status == "MATCHED"
    ).count()
    recon_accuracy_pct = _safe_pct(matched_recon, total_recon)

    # ── 2. Exception detection rate ────────────────────────────────────────
    total_orders = db.query(Order).count()
    total_exceptions = db.query(FinancialException).count()
    exception_rate_pct = _safe_pct(total_exceptions, max(total_orders, 1))

    by_type_raw = (
        db.query(FinancialException.exception_type, func.count())
        .group_by(FinancialException.exception_type)
        .all()
    )
    exceptions_by_type = {row[0]: row[1] for row in by_type_raw}

    # ── 3. Settlement discrepancy rate ─────────────────────────────────────
    total_settlement_calcs = db.query(SettlementCalculation).count()
    discrepancy_count = db.query(SettlementCalculation).filter(
        SettlementCalculation.calculation_status == "DISCREPANCY"
    ).count()
    correct_count = db.query(SettlementCalculation).filter(
        SettlementCalculation.calculation_status == "CORRECT"
    ).count()
    settlement_discrepancy_rate_pct = _safe_pct(discrepancy_count, total_settlement_calcs)
    settlement_accuracy_pct = _safe_pct(correct_count, total_settlement_calcs)

    # ── 4. Refund reconciliation accuracy ──────────────────────────────────
    total_refunds = db.query(RefundReconciliationResult).count()
    matched_refunds = db.query(RefundReconciliationResult).filter(
        RefundReconciliationResult.refund_status == "REFUND_MATCHED"
    ).count()
    refund_accuracy_pct = _safe_pct(matched_refunds, total_refunds)

    refund_by_status_raw = (
        db.query(RefundReconciliationResult.refund_status, func.count())
        .group_by(RefundReconciliationResult.refund_status)
        .all()
    )
    refund_by_status = {row[0]: row[1] for row in refund_by_status_raw}

    # ── 5. Tax reconciliation accuracy ─────────────────────────────────────
    total_tax = db.query(TaxReconciliationResult).count()
    matched_tax = db.query(TaxReconciliationResult).filter(
        TaxReconciliationResult.status == "MATCHED"
    ).count()
    tax_accuracy_pct = _safe_pct(matched_tax, total_tax)

    # ── 6. Average resolution time ─────────────────────────────────────────
    resolved_cases = db.query(FinancialException).filter(
        FinancialException.status.in_(["RESOLVED", "DISMISSED"])
    ).all()

    avg_resolution_hours: Optional[float] = None
    if resolved_cases:
        total_hours = sum(
            max(0.0, (c.updated_at - c.detected_at).total_seconds() / 3600)
            for c in resolved_cases
            if c.updated_at and c.detected_at
        )
        avg_resolution_hours = round(total_hours / len(resolved_cases), 1)

    # ── 7. Open cases by risk ──────────────────────────────────────────────
    open_cases_raw = (
        db.query(FinancialException.risk_level, func.count())
        .filter(FinancialException.status.in_(["OPEN", "ASSIGNED", "IN_REVIEW", "ESCALATED"]))
        .group_by(FinancialException.risk_level)
        .all()
    )
    open_cases_by_risk = {row[0]: row[1] for row in open_cases_raw}
    total_open_cases = sum(open_cases_by_risk.values())

    # ── 8. Status distribution ─────────────────────────────────────────────
    status_dist_raw = (
        db.query(FinancialException.status, func.count())
        .group_by(FinancialException.status)
        .all()
    )
    status_distribution = {row[0]: row[1] for row in status_dist_raw}

    # ── 9. Audit trail stats ───────────────────────────────────────────────
    total_audit_events = db.query(AuditTrailEvent).count()
    audit_by_type_raw = (
        db.query(AuditTrailEvent.event_type, func.count())
        .group_by(AuditTrailEvent.event_type)
        .all()
    )
    audit_by_type = {row[0]: row[1] for row in audit_by_type_raw}

    # ── 10. Captured vs settled payments ──────────────────────────────────
    total_captured = db.query(Payment).filter(Payment.status == "captured").count()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Evaluation metrics only. Do not use for financial decisions.",

        "reconciliation": {
            "total_records": total_recon,
            "matched": matched_recon,
            "accuracy_pct": recon_accuracy_pct,
        },

        "settlement_calculations": {
            "total": total_settlement_calcs,
            "correct": correct_count,
            "discrepancy": discrepancy_count,
            "accuracy_pct": settlement_accuracy_pct,
            "discrepancy_rate_pct": settlement_discrepancy_rate_pct,
        },

        "refund_reconciliation": {
            "total": total_refunds,
            "matched": matched_refunds,
            "accuracy_pct": refund_accuracy_pct,
            "by_status": refund_by_status,
        },

        "tax_reconciliation": {
            "total": total_tax,
            "matched": matched_tax,
            "accuracy_pct": tax_accuracy_pct,
        },

        "exception_detection": {
            "total_orders": total_orders,
            "total_exceptions": total_exceptions,
            "detection_rate_pct": exception_rate_pct,
            "by_type": exceptions_by_type,
        },

        "resolution_performance": {
            "resolved_cases": len(resolved_cases),
            "avg_resolution_hours": avg_resolution_hours,
            "total_open_cases": total_open_cases,
            "open_by_risk": open_cases_by_risk,
            "status_distribution": status_distribution,
        },

        "audit_trail": {
            "total_events": total_audit_events,
            "by_event_type": audit_by_type,
        },

        "payment_posture": {
            "total_captured_payments": total_captured,
        },

        "ground_truth": {
            "note": (
                "Ground truth data is loaded from data/demo/ground_truth.csv for evaluation only. "
                "It is NEVER used in production reconciliation, forecasting, or exception detection logic."
            ),
            "available": os.path.exists("data/demo/ground_truth.csv"),
        },
    }
