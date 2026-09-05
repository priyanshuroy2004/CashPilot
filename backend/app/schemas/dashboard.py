"""
Pydantic schemas for Dashboard Overview metrics.
"""
from typing import Dict, Optional, Any
from pydantic import BaseModel


class BreakdownCounters(BaseModel):
    matched: int = 0
    matched_with_tolerance: int = 0
    payment_missing: int = 0
    amount_mismatch: int = 0
    failed_payment: int = 0
    order_missing: int = 0
    pending_bank_credit: int = 0
    mismatch: int = 0
    needs_review: int = 0
    total: int = 0


class DashboardOverviewResponse(BaseModel):
    has_data: bool = True
    total_orders: int = 0
    total_orders_amount: int = 0  # paise
    total_captured_payments: int = 0
    total_captured_amount: int = 0  # paise
    total_settlements: int = 0
    total_settlements_net: int = 0  # paise
    total_bank_credits: int = 0
    total_bank_credits_amount: int = 0  # paise
    
    # Reconciliation Metrics
    matched_records: int = 0
    pending_missing_records: int = 0
    exception_count: int = 0
    value_at_risk: int = 0  # paise
    
    # Breakdowns
    orders_payments: Dict[str, Any] = {}
    settlements_bank: Dict[str, Any] = {}
