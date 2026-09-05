"""
Reconciliation Engine Orchestrator.

Coordinates order-payment and settlement-bank matching,
persists structured results to PostgreSQL, and computes summary statistics.
"""

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.models import (
    BankTransaction,
    Order,
    Payment,
    ReconciliationResult,
    Settlement,
)
from app.services.reconciliation.order_payment import ReconItem, reconcile_orders_payments
from app.services.reconciliation.settlement_bank import reconcile_settlements_bank


class ReconciliationEngine:
    def __init__(self, db: Session, tolerance_paise: int = 1, date_window_days: int = 7):
        self.db = db
        self.tolerance_paise = tolerance_paise
        self.date_window_days = date_window_days

    def run(self) -> Dict[str, Any]:
        """
        Execute full reconciliation across all entities in the database.
        Clears previous results and stores fresh results in reconciliation_results table.
        Returns aggregated summary.
        """
        # 1. Fetch all records from database
        orders = self.db.query(Order).all()
        payments = self.db.query(Payment).all()
        settlements = self.db.query(Settlement).all()
        bank_txns = self.db.query(BankTransaction).all()

        # 2. Run deterministic matching modules
        op_results: List[ReconItem] = reconcile_orders_payments(
            orders=orders,
            payments=payments,
            tolerance=0,
        )

        sb_results: List[ReconItem] = reconcile_settlements_bank(
            settlements=settlements,
            bank_transactions=bank_txns,
            tolerance=self.tolerance_paise,
            date_window_days=self.date_window_days,
        )

        all_results = op_results + sb_results

        # 3. Clear existing reconciliation results
        self.db.query(ReconciliationResult).delete(synchronize_session=False)

        # 4. Insert all new reconciliation results
        db_objects = [
            ReconciliationResult(
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                related_entity_id=item.related_entity_id,
                match_type=item.match_type,
                status=item.status,
                confidence=item.confidence,
                expected_amount=item.expected_amount,
                actual_amount=item.actual_amount,
                difference=item.difference,
                reason=item.reason,
                created_at=datetime.utcnow(),
            )
            for item in all_results
        ]
        self.db.bulk_save_objects(db_objects)
        self.db.commit()

        # 5. Build summary breakdown
        summary = self.get_summary(op_results, sb_results)
        return summary

    def get_summary(
        self,
        op_results: Optional[List[ReconItem]] = None,
        sb_results: Optional[List[ReconItem]] = None,
    ) -> Dict[str, Any]:
        """Compute aggregated counts from memory or database."""
        if op_results is None or sb_results is None:
            # Query from database
            rows = self.db.query(ReconciliationResult).all()
            op_items = [r for r in rows if r.entity_type in ("ORDER", "PAYMENT")]
            sb_items = [r for r in rows if r.entity_type in ("SETTLEMENT", "BANK_TRANSACTION")]
        else:
            op_items = op_results
            sb_items = sb_results

        # Order / Payment stats
        op_matched = sum(1 for r in op_items if r.status == "MATCHED")
        op_mismatch = sum(1 for r in op_items if r.status == "AMOUNT_MISMATCH")
        op_missing_pay = sum(1 for r in op_items if r.status == "PAYMENT_MISSING")
        op_missing_order = sum(1 for r in op_items if r.status == "ORDER_MISSING")
        op_failed = sum(1 for r in op_items if r.status == "FAILED_PAYMENT")
        op_review = sum(1 for r in op_items if r.status == "NEEDS_REVIEW")

        # Settlement / Bank stats
        sb_matched = sum(1 for r in sb_items if r.status in ("MATCHED", "MATCHED_WITH_TOLERANCE"))
        sb_pending = sum(1 for r in sb_items if r.status == "PENDING_BANK_CREDIT")
        sb_mismatch = sum(1 for r in sb_items if r.status == "MISMATCH")
        sb_review = sum(1 for r in sb_items if r.status == "NEEDS_REVIEW")

        return {
            "orders_payments": {
                "matched": op_matched,
                "amount_mismatch": op_mismatch,
                "payment_missing": op_missing_pay,
                "order_missing": op_missing_order,
                "failed": op_failed,
                "needs_review": op_review,
                "total": len(op_items),
            },
            "settlements_bank": {
                "matched": sb_matched,
                "pending": sb_pending,
                "mismatch": sb_mismatch,
                "needs_review": sb_review,
                "total": len(sb_items),
            },
            "total_records": len(op_items) + len(sb_items),
        }
