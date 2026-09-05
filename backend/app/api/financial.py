"""
Phase 2A Financial Intelligence API endpoints.

Endpoints:
  POST /api/financial/run                         — run all 3 Phase 2A engines
  POST /api/financial/run-settlement-calculations — run only calculator
  POST /api/financial/run-tax-matching            — run only tax matcher
  POST /api/financial/run-refund-matching         — run only refund matcher
  GET  /api/financial/summary                     — current Phase 2A status counts
  GET  /api/financial/settlement-calculations     — paginated calc results
  GET  /api/financial/settlement-calculations/{id} — single calc detail
  GET  /api/financial/tax-reconciliation          — paginated tax-line results
  GET  /api/financial/refund-reconciliation       — paginated refund results
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.models import (
    SettlementCalculation,
    TaxReconciliationResult,
    RefundReconciliationResult,
)
from app.schemas.financial import (
    FinancialRunResponse,
    FinancialSummaryResponse,
    SettlementCalculationSummary,
    TaxReconciliationSummary,
    RefundReconciliationSummary,
    SettlementCalculationResponse,
    PaginatedSettlementCalculations,
    TaxReconciliationResultResponse,
    PaginatedTaxReconciliation,
    RefundReconciliationResultResponse,
    PaginatedRefundReconciliation,
)
from app.services.financial_intelligence.settlement_calculator import run_settlement_calculations
from app.services.financial_intelligence.tax_matcher import run_tax_matching
from app.services.financial_intelligence.refund_matcher import run_refund_matching

router = APIRouter(prefix="/api/financial", tags=["financial"])


# ---------------------------------------------------------------------------
# Helper: build summary from DB state
# ---------------------------------------------------------------------------

def _get_settlement_calc_summary(db: Session) -> SettlementCalculationSummary:
    total = db.query(SettlementCalculation).count()
    correct = db.query(SettlementCalculation).filter(
        SettlementCalculation.calculation_status == "CORRECT"
    ).count()
    discrepancy = db.query(SettlementCalculation).filter(
        SettlementCalculation.calculation_status == "DISCREPANCY"
    ).count()
    return SettlementCalculationSummary(total=total, correct=correct, discrepancy=discrepancy)


def _get_tax_recon_summary(db: Session) -> TaxReconciliationSummary:
    rows = db.query(TaxReconciliationResult).all()
    by_status: dict = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    settlements_checked = len(
        set(r.settlement_id for r in rows)
    )
    return TaxReconciliationSummary(
        total_checks=len(rows),
        settlements_checked=settlements_checked,
        by_status=by_status,
    )


def _get_refund_recon_summary(db: Session) -> RefundReconciliationSummary:
    rows = db.query(RefundReconciliationResult).all()
    by_status: dict = {}
    for r in rows:
        by_status[r.refund_status] = by_status.get(r.refund_status, 0) + 1
    return RefundReconciliationSummary(
        total_refunds=len(rows),
        by_status=by_status,
    )


# ---------------------------------------------------------------------------
# POST /api/financial/run
# ---------------------------------------------------------------------------

@router.post("/run", response_model=FinancialRunResponse)
def run_all_financial_intelligence(
    tolerance_paise: int = Query(default=1, ge=0, description="Tolerance in paise for net calculation matching"),
    db: Session = Depends(get_db),
):
    """
    Run all three Phase 2A Financial Intelligence engines in sequence:
      1. Settlement fee/tax/net calculator
      2. Tax-line matching (settlement vs ledger)
      3. Refund reconciliation (gateway → settlement → ledger)

    Clears previous Phase 2A results and recomputes from scratch.
    Safe to call after demo data reload.
    """
    try:
        calc_counts = run_settlement_calculations(db, tolerance=tolerance_paise)
        tax_counts = run_tax_matching(db)
        refund_counts = run_refund_matching(db)

        return FinancialRunResponse(
            success=True,
            message="Financial intelligence engines executed successfully.",
            settlement_calculations=SettlementCalculationSummary(
                total=calc_counts["total"],
                correct=calc_counts["correct"],
                discrepancy=calc_counts["discrepancy"],
            ),
            tax_reconciliation=TaxReconciliationSummary(
                total_checks=tax_counts["total_checks"],
                settlements_checked=tax_counts["settlements_checked"],
                by_status=tax_counts["by_status"],
            ),
            refund_reconciliation=RefundReconciliationSummary(
                total_refunds=refund_counts["total_refunds"],
                by_status=refund_counts["by_status"],
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Financial intelligence engine failed: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/financial/run-settlement-calculations
# ---------------------------------------------------------------------------

@router.post("/run-settlement-calculations", response_model=SettlementCalculationSummary)
def run_only_settlement_calculations(
    tolerance_paise: int = Query(default=1, ge=0),
    db: Session = Depends(get_db),
):
    """Run only the settlement fee/tax/net calculation engine."""
    try:
        counts = run_settlement_calculations(db, tolerance=tolerance_paise)
        return SettlementCalculationSummary(
            total=counts["total"],
            correct=counts["correct"],
            discrepancy=counts["discrepancy"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/financial/run-tax-matching
# ---------------------------------------------------------------------------

@router.post("/run-tax-matching", response_model=TaxReconciliationSummary)
def run_only_tax_matching(db: Session = Depends(get_db)):
    """Run only the tax-line matching engine (settlement components vs ledger)."""
    try:
        counts = run_tax_matching(db)
        return TaxReconciliationSummary(
            total_checks=counts["total_checks"],
            settlements_checked=counts["settlements_checked"],
            by_status=counts["by_status"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/financial/run-refund-matching
# ---------------------------------------------------------------------------

@router.post("/run-refund-matching", response_model=RefundReconciliationSummary)
def run_only_refund_matching(db: Session = Depends(get_db)):
    """Run only the refund reconciliation engine."""
    try:
        counts = run_refund_matching(db)
        return RefundReconciliationSummary(
            total_refunds=counts["total_refunds"],
            by_status=counts["by_status"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /api/financial/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=FinancialSummaryResponse)
def get_financial_summary(db: Session = Depends(get_db)):
    """
    Return current Phase 2A status counts from the database
    (no re-run, just read existing results).
    """
    return FinancialSummaryResponse(
        settlement_calculations=_get_settlement_calc_summary(db),
        tax_reconciliation=_get_tax_recon_summary(db),
        refund_reconciliation=_get_refund_recon_summary(db),
    )


# ---------------------------------------------------------------------------
# GET /api/financial/settlement-calculations
# ---------------------------------------------------------------------------

@router.get("/settlement-calculations", response_model=PaginatedSettlementCalculations)
def get_settlement_calculations(
    status: Optional[str] = Query(default=None, description="Filter by status: CORRECT | DISCREPANCY"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get paginated settlement fee/tax/net calculation results."""
    query = db.query(SettlementCalculation)
    if status:
        query = query.filter(SettlementCalculation.calculation_status == status.upper())
    total = query.count()
    items = query.order_by(SettlementCalculation.id.asc()).offset(offset).limit(limit).all()
    return PaginatedSettlementCalculations(
        items=[SettlementCalculationResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/financial/settlement-calculations/{settlement_id}
# ---------------------------------------------------------------------------

@router.get("/settlement-calculations/{settlement_id}", response_model=SettlementCalculationResponse)
def get_single_settlement_calculation(settlement_id: str, db: Session = Depends(get_db)):
    """Get the fee/tax/net calculation detail for a specific settlement."""
    row = db.query(SettlementCalculation).filter(
        SettlementCalculation.settlement_id == settlement_id
    ).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No calculation found for settlement {settlement_id}. Run /api/financial/run first.",
        )
    return SettlementCalculationResponse.model_validate(row)


# ---------------------------------------------------------------------------
# GET /api/financial/tax-reconciliation
# ---------------------------------------------------------------------------

@router.get("/tax-reconciliation", response_model=PaginatedTaxReconciliation)
def get_tax_reconciliation(
    status: Optional[str] = Query(default=None, description="Filter: MATCHED | MISSING_LEDGER_ENTRY | AMOUNT_MISMATCH | DUPLICATE_ENTRY"),
    component: Optional[str] = Query(default=None, description="Filter by component: FEE | TAX | REFUND | NET"),
    settlement_id: Optional[str] = Query(default=None, description="Filter by settlement ID"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get paginated tax-line reconciliation results."""
    query = db.query(TaxReconciliationResult)
    if status:
        query = query.filter(TaxReconciliationResult.status == status.upper())
    if component:
        query = query.filter(TaxReconciliationResult.component == component.upper())
    if settlement_id:
        query = query.filter(TaxReconciliationResult.settlement_id == settlement_id)
    total = query.count()
    items = query.order_by(TaxReconciliationResult.id.asc()).offset(offset).limit(limit).all()
    return PaginatedTaxReconciliation(
        items=[TaxReconciliationResultResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /api/financial/refund-reconciliation
# ---------------------------------------------------------------------------

@router.get("/refund-reconciliation", response_model=PaginatedRefundReconciliation)
def get_refund_reconciliation(
    status: Optional[str] = Query(default=None, description="Filter by refund_status"),
    payment_id: Optional[str] = Query(default=None),
    settlement_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get paginated refund reconciliation results."""
    query = db.query(RefundReconciliationResult)
    if status:
        query = query.filter(RefundReconciliationResult.refund_status == status.upper())
    if payment_id:
        query = query.filter(RefundReconciliationResult.payment_id == payment_id)
    if settlement_id:
        query = query.filter(RefundReconciliationResult.settlement_id == settlement_id)
    total = query.count()
    items = query.order_by(RefundReconciliationResult.id.asc()).offset(offset).limit(limit).all()
    return PaginatedRefundReconciliation(
        items=[RefundReconciliationResultResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
