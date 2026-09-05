"""
Pydantic schemas for Exception items, lists, and details.
"""
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, model_validator


class MatchingMethodCheck(BaseModel):
    method: str
    attempted: bool
    passed: bool
    details: Optional[str] = None


class ExceptionDetail(BaseModel):
    id: int
    exception_id: str
    exception_type: str
    entity_type: str
    entity_id: str
    related_entity_id: Optional[str] = None
    amount_at_risk: int  # paise
    severity: str        # HIGH | MEDIUM | LOW
    status: str          # OPEN | IN_REVIEW | RESOLVED
    match_type: Optional[str] = None
    confidence: Optional[float] = None
    expected_amount: Optional[int] = None
    actual_amount: Optional[int] = None
    difference: Optional[int] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
    methods_attempted: List[MatchingMethodCheck] = []
    recommended_action: Optional[str] = None


class ExceptionSummaryResponse(BaseModel):
    total_exceptions: int = 0
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0
    total_value_at_risk: int = 0  # paise
    by_type: Dict[str, int] = {}


class PaginatedExceptions(BaseModel):
    total: int
    items: List[ExceptionDetail]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Phase 2B: Financial Investigation Exception Schemas
# ---------------------------------------------------------------------------
class FinancialExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    exception_type: str
    risk_level: str
    value_at_risk: int
    value_at_risk_inr: Optional[str] = None
    status: str
    suggested_owner: str
    related_order_id: Optional[str] = None
    related_payment_id: Optional[str] = None
    related_settlement_id: Optional[str] = None
    related_bank_entry_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    explanation: str
    triggering_rule: str
    detected_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None

    @model_validator(mode="after")
    def populate_inr(self):
        if self.value_at_risk is not None and not self.value_at_risk_inr:
            self.value_at_risk_inr = f"₹{self.value_at_risk / 100.0:,.2f}"
        return self


class PaginatedFinancialExceptions(BaseModel):
    total: int
    items: List[FinancialExceptionResponse]
    limit: int
    offset: int


class ExceptionDetectionRunResponse(BaseModel):
    success: bool
    message: str
    total_exceptions: int
    total_value_at_risk_paise: int
    total_value_at_risk_inr: str
    by_type: Dict[str, int]
    by_risk: Dict[str, int]
    unfulfilled_detected: int
    settlement_missing_detected: int
    other_anomalies_detected: int


class ExceptionStatusUpdateRequest(BaseModel):
    status: str  # OPEN | ASSIGNED | IN_REVIEW | RESOLVED | DISMISSED | ESCALATED
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None


class FinancialExceptionsSummary(BaseModel):
    total_cases: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_value_at_risk_paise: int
    total_value_at_risk_inr: str
    by_type: Dict[str, int]
    by_owner: Dict[str, int]
    by_status: Dict[str, int]

