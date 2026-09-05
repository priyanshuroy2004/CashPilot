"""
Pydantic schemas for reconciliation endpoints.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReconciliationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: str
    related_entity_id: Optional[str] = None
    match_type: Optional[str] = None
    status: str
    confidence: Optional[float] = None
    expected_amount: Optional[int] = None
    actual_amount: Optional[int] = None
    difference: Optional[int] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


class OrdersPaymentsSummary(BaseModel):
    matched: int = 0
    amount_mismatch: int = 0
    payment_missing: int = 0
    order_missing: int = 0
    failed: int = 0
    needs_review: int = 0
    total: int = 0


class SettlementsBankSummary(BaseModel):
    matched: int = 0
    pending: int = 0
    mismatch: int = 0
    needs_review: int = 0
    total: int = 0


class ReconciliationSummaryResponse(BaseModel):
    orders_payments: OrdersPaymentsSummary
    settlements_bank: SettlementsBankSummary
    total_records: int


class ReconRunResponse(BaseModel):
    success: bool = True
    message: str = "Reconciliation completed successfully"
    orders_payments: OrdersPaymentsSummary
    settlements_bank: SettlementsBankSummary
    total_records: int


class PaginatedReconResults(BaseModel):
    items: List[ReconciliationItemResponse]
    total: int
    limit: int
    offset: int
