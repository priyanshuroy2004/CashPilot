"""
Dashboard aggregation service.
Computes real-time financial metrics from PostgreSQL database.
Zero hardcoded metrics.
"""
from typing import Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    Order,
    Payment,
    Settlement,
    BankTransaction,
    ReconciliationResult,
)
from app.schemas.dashboard import DashboardOverviewResponse


def get_dashboard_overview_metrics(db: Session) -> DashboardOverviewResponse:
    """
    Computes full live dashboard overview metrics directly from database tables.
    """
    # 1. Orders metrics
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_orders_amount = db.query(func.sum(Order.order_amount)).scalar() or 0

    # 2. Payments metrics (captured)
    total_captured_payments = (
        db.query(func.count(Payment.id))
        .filter(func.lower(Payment.status) == "captured")
        .scalar()
        or 0
    )
    total_captured_amount = (
        db.query(func.sum(Payment.amount))
        .filter(func.lower(Payment.status) == "captured")
        .scalar()
        or 0
    )

    # 3. Settlements metrics
    total_settlements = db.query(func.count(Settlement.id)).scalar() or 0
    total_settlements_net = db.query(func.sum(Settlement.net_amount)).scalar() or 0

    # 4. Bank Credits metrics
    total_bank_credits = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.direction == "CREDIT")
        .scalar()
        or 0
    )
    total_bank_credits_amount = (
        db.query(func.sum(BankTransaction.amount))
        .filter(BankTransaction.direction == "CREDIT")
        .scalar()
        or 0
    )

    has_data = (total_orders > 0) or (total_settlements > 0) or (total_bank_credits > 0)

    # 5. Reconciliation Results metrics
    recon_rows = db.query(ReconciliationResult).all()

    matched_records = 0
    pending_missing_records = 0
    exception_count = 0
    value_at_risk = 0

    op_counters = {
        "matched": 0,
        "amount_mismatch": 0,
        "payment_missing": 0,
        "order_missing": 0,
        "failed": 0,
        "needs_review": 0,
        "total": 0,
    }

    sb_counters = {
        "matched": 0,
        "pending": 0,
        "mismatch": 0,
        "needs_review": 0,
        "total": 0,
    }

    for row in recon_rows:
        etype = str(row.entity_type).upper()
        status = str(row.status).upper()

        if etype in ("ORDER", "PAYMENT"):
            op_counters["total"] += 1
            if status in ("MATCHED", "MATCHED_WITH_TOLERANCE"):
                op_counters["matched"] += 1
                matched_records += 1
            elif status == "AMOUNT_MISMATCH":
                op_counters["amount_mismatch"] += 1
                exception_count += 1
                value_at_risk += abs(row.difference or 0)
            elif status == "PAYMENT_MISSING":
                op_counters["payment_missing"] += 1
                pending_missing_records += 1
                exception_count += 1
                value_at_risk += abs(row.expected_amount or 0)
            elif status == "ORDER_MISSING":
                op_counters["order_missing"] += 1
                pending_missing_records += 1
                exception_count += 1
                value_at_risk += abs(row.actual_amount or 0)
            elif status == "FAILED_PAYMENT":
                op_counters["failed"] += 1
                exception_count += 1
                value_at_risk += abs(row.expected_amount or 0)
            elif status == "NEEDS_REVIEW":
                op_counters["needs_review"] += 1
                exception_count += 1
                value_at_risk += abs(row.difference if row.difference != 0 else (row.expected_amount or 0))
            else:
                exception_count += 1

        elif etype == "SETTLEMENT":
            sb_counters["total"] += 1
            if status in ("MATCHED", "MATCHED_WITH_TOLERANCE"):
                sb_counters["matched"] += 1
                matched_records += 1
            elif status == "PENDING_BANK_CREDIT":
                sb_counters["pending"] += 1
                pending_missing_records += 1
                exception_count += 1
                value_at_risk += abs(row.expected_amount or 0)
            elif status == "MISMATCH":
                sb_counters["mismatch"] += 1
                exception_count += 1
                value_at_risk += abs(row.difference or 0)
            elif status == "NEEDS_REVIEW":
                sb_counters["needs_review"] += 1
                exception_count += 1
                value_at_risk += abs(row.difference if row.difference != 0 else (row.expected_amount or 0))
            else:
                exception_count += 1

    return DashboardOverviewResponse(
        has_data=has_data,
        total_orders=total_orders,
        total_orders_amount=total_orders_amount,
        total_captured_payments=total_captured_payments,
        total_captured_amount=total_captured_amount,
        total_settlements=total_settlements,
        total_settlements_net=total_settlements_net,
        total_bank_credits=total_bank_credits,
        total_bank_credits_amount=total_bank_credits_amount,
        matched_records=matched_records,
        pending_missing_records=pending_missing_records,
        exception_count=exception_count,
        value_at_risk=value_at_risk,
        orders_payments=op_counters,
        settlements_bank=sb_counters,
    )
