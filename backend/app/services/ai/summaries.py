"""
Executive Summaries and Daily Finance Briefings for CashPilot AI.
"""
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models.models import (
    FinancialException,
    SettlementCalculation,
    TaxReconciliationResult,
    RefundReconciliationResult,
)
from app.schemas.ai import DailyExceptionSummaryResponse
from app.services.ai.evidence_builder import (
    build_cash_position_evidence_package,
    build_highest_risk_evidence_package,
)
from app.services.ai.client import ai_client


def generate_daily_executive_summary(db: Session) -> DailyExceptionSummaryResponse:
    """
    Assembles enterprise-wide financial evidence across all modules
    and generates a high-level briefing for CFO / Finance Lead.
    """
    # 1. Cash Posture
    cash_posture = build_cash_position_evidence_package(db)

    # 2. Highest Risk Items
    highest_risk = build_highest_risk_evidence_package(db, limit=5)

    # 3. Settlement Calculation Metrics
    total_calcs = db.query(SettlementCalculation).count()
    correct_calcs = (
        db.query(SettlementCalculation)
        .filter(SettlementCalculation.calculation_status == "CORRECT")
        .count()
    )
    settlement_accuracy_pct = (
        round((correct_calcs / total_calcs * 100.0), 1) if total_calcs > 0 else 100.0
    )

    # 4. Tax lines status
    tax_anomalies_count = (
        db.query(TaxReconciliationResult)
        .filter(TaxReconciliationResult.status != "MATCHED")
        .count()
    )

    # 5. Refund anomalies count
    refund_anomalies_count = (
        db.query(RefundReconciliationResult)
        .filter(RefundReconciliationResult.refund_status != "MATCHED")
        .count()
    )

    # 6. Assemble complete package
    summary_evidence: Dict[str, Any] = {
        "cash_posture": cash_posture,
        "highest_risk": highest_risk,
        "key_metrics": {
            "settlement_accuracy_rate": f"{settlement_accuracy_pct}%",
            "open_exceptions_total": cash_posture.get("at_risk_case_count", 0),
            "tax_line_discrepancies": tax_anomalies_count,
            "unposted_refund_discrepancies": refund_anomalies_count,
            "total_value_at_risk": cash_posture.get("at_risk_inr", "₹0.00"),
        },
    }

    return ai_client.generate_executive_summary(summary_evidence)
