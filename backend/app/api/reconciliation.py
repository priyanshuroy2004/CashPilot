"""
FastAPI router for deterministic reconciliation endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.models import ReconciliationResult
from app.schemas.reconciliation import (
    PaginatedReconResults,
    ReconciliationItemResponse,
    ReconciliationSummaryResponse,
    ReconRunResponse,
)
from app.services.reconciliation.engine import ReconciliationEngine

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.post("/run", response_model=ReconRunResponse)
def run_reconciliation(
    tolerance_paise: int = Query(default=1, ge=0, description="Tolerance in paise (1 paise = 0.01 INR)"),
    db: Session = Depends(get_db),
):
    """
    Run full deterministic reconciliation for the currently loaded merchant dataset.
    Prioritizes financial correctness over match rate.
    Clears previous results and stores new results in the database.
    """
    try:
        engine = ReconciliationEngine(db=db, tolerance_paise=tolerance_paise)
        summary = engine.run()
        return ReconRunResponse(
            success=True,
            message="Reconciliation executed successfully",
            orders_payments=summary["orders_payments"],
            settlements_bank=summary["settlements_bank"],
            total_records=summary["total_records"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation engine failed: {str(e)}",
        )


@router.get("/summary", response_model=ReconciliationSummaryResponse)
def get_reconciliation_summary(db: Session = Depends(get_db)):
    """
    Get aggregated summary counts for the most recent reconciliation run.
    """
    engine = ReconciliationEngine(db=db)
    summary = engine.get_summary()
    return ReconciliationSummaryResponse(
        orders_payments=summary["orders_payments"],
        settlements_bank=summary["settlements_bank"],
        total_records=summary["total_records"],
    )


@router.get("/orders-payments", response_model=PaginatedReconResults)
def get_order_payment_reconciliation(
    status: Optional[str] = Query(default=None, description="Filter by status (MATCHED, AMOUNT_MISMATCH, PAYMENT_MISSING, ORDER_MISSING, FAILED_PAYMENT, NEEDS_REVIEW)"),
    search: Optional[str] = Query(default=None, description="Search by entity_id or related_entity_id"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get paginated Order ↔ Payment reconciliation results with optional filters.
    """
    query = db.query(ReconciliationResult).filter(
        ReconciliationResult.entity_type.in_(["ORDER", "PAYMENT"])
    )

    if status:
        query = query.filter(ReconciliationResult.status == status.upper())

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ReconciliationResult.entity_id.ilike(search_pattern),
                ReconciliationResult.related_entity_id.ilike(search_pattern),
                ReconciliationResult.reason.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(ReconciliationResult.id.asc()).offset(offset).limit(limit).all()

    return PaginatedReconResults(
        items=[ReconciliationItemResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/settlements-bank", response_model=PaginatedReconResults)
def get_settlement_bank_reconciliation(
    status: Optional[str] = Query(default=None, description="Filter by status (MATCHED, MATCHED_WITH_TOLERANCE, PENDING_BANK_CREDIT, MISMATCH, NEEDS_REVIEW)"),
    search: Optional[str] = Query(default=None, description="Search by settlement_id, UTR, or bank entry ID"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get paginated Settlement ↔ Bank reconciliation results with optional filters.
    """
    query = db.query(ReconciliationResult).filter(
        ReconciliationResult.entity_type.in_(["SETTLEMENT", "BANK_TRANSACTION"])
    )

    if status:
        query = query.filter(ReconciliationResult.status == status.upper())

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ReconciliationResult.entity_id.ilike(search_pattern),
                ReconciliationResult.related_entity_id.ilike(search_pattern),
                ReconciliationResult.reason.ilike(search_pattern),
            )
        )

    total = query.count()
    items = query.order_by(ReconciliationResult.id.asc()).offset(offset).limit(limit).all()

    return PaginatedReconResults(
        items=[ReconciliationItemResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
