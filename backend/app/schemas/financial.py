"""
Phase 2A Financial Intelligence Pydantic schemas.

All monetary amounts are returned in BOTH paise (integer) and INR (float, 2dp)
so the frontend can display either without conversion logic on the client side.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator, model_validator


def _paise_to_inr(paise: Optional[int]) -> Optional[float]:
    """Convert paise (BigInteger) to INR with 2 decimal places."""
    if paise is None:
        return None
    return round(paise / 100, 2)


# ---------------------------------------------------------------------------
# Settlement Calculation schemas
# ---------------------------------------------------------------------------

class SettlementCalculationResponse(BaseModel):
    """One row from settlement_calculations table."""
    settlement_id: str
    gross_amount: int                   # paise
    fee_amount: int                     # paise
    tax_amount: int                     # paise
    refund_adjustment: int              # paise
    other_adjustment: int               # paise
    expected_net_amount: int            # paise
    reported_net_amount: int            # paise
    calculation_status: str             # CORRECT | DISCREPANCY
    calculation_difference: int         # paise (reported - expected)
    payment_count: int
    created_at: Optional[datetime]

    # INR convenience fields (computed)
    gross_amount_inr: Optional[float] = None
    fee_amount_inr: Optional[float] = None
    tax_amount_inr: Optional[float] = None
    expected_net_inr: Optional[float] = None
    reported_net_inr: Optional[float] = None
    difference_inr: Optional[float] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_inr_fields(self) -> "SettlementCalculationResponse":
        self.gross_amount_inr = _paise_to_inr(self.gross_amount)
        self.fee_amount_inr = _paise_to_inr(self.fee_amount)
        self.tax_amount_inr = _paise_to_inr(self.tax_amount)
        self.expected_net_inr = _paise_to_inr(self.expected_net_amount)
        self.reported_net_inr = _paise_to_inr(self.reported_net_amount)
        self.difference_inr = _paise_to_inr(self.calculation_difference)
        return self


class PaginatedSettlementCalculations(BaseModel):
    items: List[SettlementCalculationResponse]
    total: int
    limit: int
    offset: int


class SettlementCalculationSummary(BaseModel):
    total: int
    correct: int
    discrepancy: int


# ---------------------------------------------------------------------------
# Tax Reconciliation schemas
# ---------------------------------------------------------------------------

class TaxReconciliationResultResponse(BaseModel):
    """One row from tax_reconciliation_results table."""
    id: int
    settlement_id: str
    component: str                      # FEE | TAX | REFUND | NET
    expected_amount: Optional[int]      # paise
    ledger_amount: Optional[int]        # paise
    difference: Optional[int]           # paise
    status: str                         # MATCHED | MISSING_LEDGER_ENTRY | AMOUNT_MISMATCH | DUPLICATE_ENTRY
    ledger_entry_id: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]

    # INR convenience fields
    expected_amount_inr: Optional[float] = None
    ledger_amount_inr: Optional[float] = None
    difference_inr: Optional[float] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_inr_fields(self) -> "TaxReconciliationResultResponse":
        self.expected_amount_inr = _paise_to_inr(self.expected_amount)
        self.ledger_amount_inr = _paise_to_inr(self.ledger_amount)
        self.difference_inr = _paise_to_inr(self.difference)
        return self


class PaginatedTaxReconciliation(BaseModel):
    items: List[TaxReconciliationResultResponse]
    total: int
    limit: int
    offset: int


class TaxReconciliationSummary(BaseModel):
    total_checks: int
    settlements_checked: int
    by_status: Dict[str, int]


# ---------------------------------------------------------------------------
# Refund Reconciliation schemas
# ---------------------------------------------------------------------------

class RefundReconciliationResultResponse(BaseModel):
    """One row from refund_reconciliation_results table."""
    id: int
    refund_id: str
    payment_id: Optional[str]
    order_id: Optional[str]
    settlement_id: Optional[str]
    ledger_entry_id: Optional[str]
    refund_amount: int                  # paise (from gateway)
    ledger_amount: Optional[int]        # paise (from ledger)
    amount_difference: Optional[int]    # paise (ledger - gateway)
    refund_status: str
    duplicate_count: int
    notes: Optional[str]
    created_at: Optional[datetime]

    # INR convenience fields
    refund_amount_inr: Optional[float] = None
    ledger_amount_inr: Optional[float] = None
    difference_inr: Optional[float] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_inr_fields(self) -> "RefundReconciliationResultResponse":
        self.refund_amount_inr = _paise_to_inr(self.refund_amount)
        self.ledger_amount_inr = _paise_to_inr(self.ledger_amount)
        self.difference_inr = _paise_to_inr(self.amount_difference)
        return self


class PaginatedRefundReconciliation(BaseModel):
    items: List[RefundReconciliationResultResponse]
    total: int
    limit: int
    offset: int


class RefundReconciliationSummary(BaseModel):
    total_refunds: int
    by_status: Dict[str, int]


# ---------------------------------------------------------------------------
# Phase 2A combined run response
# ---------------------------------------------------------------------------

class FinancialRunResponse(BaseModel):
    success: bool
    message: str
    settlement_calculations: SettlementCalculationSummary
    tax_reconciliation: TaxReconciliationSummary
    refund_reconciliation: RefundReconciliationSummary


class FinancialSummaryResponse(BaseModel):
    settlement_calculations: SettlementCalculationSummary
    tax_reconciliation: TaxReconciliationSummary
    refund_reconciliation: RefundReconciliationSummary
