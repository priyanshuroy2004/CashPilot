"""
Pydantic schemas for Phase 4 Forecast & Cash-Gap Alerts.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Settlement Forecast schemas
# ---------------------------------------------------------------------------

class ForecastRecord(BaseModel):
    id: int
    forecast_id: str
    payment_id: str
    order_id: Optional[str] = None
    settlement_id: Optional[str] = None
    expected_amount_paise: int
    expected_amount_inr: str
    horizon_days: int
    expected_settlement_date: str
    basis: str
    status: str
    payment_captured_at: Optional[str] = None
    gateway: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class PaginatedForecasts(BaseModel):
    total: int
    items: List[ForecastRecord]
    limit: int
    offset: int


class HorizonSummary(BaseModel):
    horizon_days: int
    payment_count: int
    expected_amount_paise: int
    expected_amount_inr: str


class ForecastSummary(BaseModel):
    """
    KPI summary split by horizon.

    IMPORTANT: All amounts labelled EXPECTED — not actual bank receipts.
    """
    label: str = "EXPECTED — not actual bank receipts"
    horizon_1_day: HorizonSummary
    horizon_3_days: HorizonSummary
    horizon_7_days: HorizonSummary
    horizon_14_days: HorizonSummary
    total_overdue_count: int
    total_overdue_paise: int
    total_overdue_inr: str
    pending_count: int
    pending_paise: int
    pending_inr: str


class ForecastRunResponse(BaseModel):
    success: bool
    message: str
    unsettled_payments_count: int
    forecasts_created: int
    horizon_summary: Dict[str, Any]
    gap_detection: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Cash Gap Alert schemas
# ---------------------------------------------------------------------------

class CashGapAlertResponse(BaseModel):
    id: int
    alert_id: str
    alert_type: str
    payment_id: Optional[str] = None
    settlement_id: Optional[str] = None
    order_id: Optional[str] = None
    expected_date: Optional[str] = None
    actual_date: Optional[str] = None
    gap_days: int
    gap_amount_paise: int
    gap_amount_inr: str
    severity: str
    status: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PaginatedAlerts(BaseModel):
    total: int
    items: List[CashGapAlertResponse]
    limit: int
    offset: int


class AlertsSummary(BaseModel):
    total_open: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_risk_paise: int
    total_risk_inr: str
    by_type: Dict[str, int]


class AlertAcknowledgeRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional notes on acknowledgement")
