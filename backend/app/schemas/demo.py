"""Pydantic schemas for the demo data endpoints."""
from pydantic import BaseModel


class DemoLoadResponse(BaseModel):
    success: bool
    message: str
    orders: int = 0
    payments: int = 0
    settlements: int = 0
    settlement_lines: int = 0
    bank_transactions: int = 0
    refunds: int = 0
    ledger_entries: int = 0
    shipments: int = 0


class DemoStatusResponse(BaseModel):
    orders: int
    payments: int
    settlements: int
    settlement_lines: int
    bank_transactions: int
    reconciliation_results: int
    data_imports: int
    refunds: int = 0
    ledger_entries: int = 0
    shipments: int = 0
