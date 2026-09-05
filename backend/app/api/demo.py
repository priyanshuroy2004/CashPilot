"""Demo data API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    BankTransaction,
    DataImport,
    Order,
    Payment,
    ReconciliationResult,
    Settlement,
    SettlementLine,
    Refund,
    LedgerEntry,
    Shipment,
)
from app.schemas import DemoLoadResponse, DemoStatusResponse
from app.services.data_ingestion.loader import load_demo_data, _clear_all_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/clear", summary="Clear all merchant and reconciliation data")
def clear_demo(db: Session = Depends(get_db)):
    """Clear all data from the database safely to return to the clean initial state."""
    try:
        _clear_all_data(db)
        return {"success": True, "message": "All data cleared successfully. Database is now in initial clean state."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {exc}")


@router.post("/load", response_model=DemoLoadResponse, summary="Load demo merchant data")
def load_demo(db: Session = Depends(get_db)):
    """
    Load the synthetic demo merchant dataset into the database.

    This endpoint:
    1. Clears all existing data safely (in dependency order).
    2. Loads orders, payments, settlements, settlement lines, bank transactions, refunds, ledger, shipments.
    3. Creates a data_imports audit record.
    4. Returns counts of records loaded.
    """
    try:
        counts = load_demo_data(db)
        return DemoLoadResponse(
            success=True,
            message="Demo data loaded successfully.",
            **counts,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Demo CSV file not found: {exc}. Run generate_demo_data.py first.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to load demo data: {exc}")


@router.get("/status", response_model=DemoStatusResponse, summary="Get current data counts")
def demo_status(db: Session = Depends(get_db)):
    """Return the current row counts for all tables."""
    return DemoStatusResponse(
        orders=db.query(Order).count(),
        payments=db.query(Payment).count(),
        settlements=db.query(Settlement).count(),
        settlement_lines=db.query(SettlementLine).count(),
        bank_transactions=db.query(BankTransaction).count(),
        reconciliation_results=db.query(ReconciliationResult).count(),
        data_imports=db.query(DataImport).count(),
        refunds=db.query(Refund).count(),
        ledger_entries=db.query(LedgerEntry).count(),
        shipments=db.query(Shipment).count(),
    )
