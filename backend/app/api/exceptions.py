"""
Exceptions REST API endpoints.
Provides:
  1. Central Financial Exceptions investigation cases (Phase 2B)
  2. Reconciliation-derived exception views (Phase 1 backward compatibility)
  3. Interactive Exception Detection runner
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models.models import FinancialException
from app.schemas.exceptions import (
    ExceptionDetail,
    ExceptionSummaryResponse,
    PaginatedExceptions,
    FinancialExceptionResponse,
    PaginatedFinancialExceptions,
    ExceptionDetectionRunResponse,
    ExceptionStatusUpdateRequest,
    FinancialExceptionsSummary,
)
from app.services.exceptions import (
    get_exceptions_list,
    get_exceptions_summary,
    get_exception_by_id,
)
from app.services.exceptions.detectors import run_all_exception_detection
from app.services.audit.trail import log_event

router = APIRouter(prefix="/api/exceptions", tags=["Exceptions"])


# ---------------------------------------------------------------------------
# Phase 2B: Detection Runner
# ---------------------------------------------------------------------------
@router.post("/detect", response_model=ExceptionDetectionRunResponse, summary="Run exception detection engine")
def run_detection(
    unfulfilled_threshold_hours: float = Query(72.0, ge=1.0, description="Hours without shipment to flag as unfulfilled"),
    settlement_window_hours: float = Query(48.0, ge=1.0, description="Hours without bank credit to flag missing settlement"),
    as_of: Optional[str] = Query(None, description="Optional evaluation timestamp (YYYY-MM-DD HH:MM:SS)"),
    db: Session = Depends(get_db),
):
    """
    Executes deterministic exception detection across:
      - PAID_BUT_UNFULFILLED (captured payment missing shipment confirmation)
      - SETTLEMENT_MISSING_IN_BANK (settlement past bank credit window)
      - RECONCILIATION & CALCULATION ANOMALIES
    """
    parsed_as_of = None
    if as_of:
        try:
            parsed_as_of = datetime.strptime(as_of, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                parsed_as_of = datetime.strptime(as_of, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid as_of format. Use YYYY-MM-DD HH:MM:SS")

    try:
        res = run_all_exception_detection(
            db=db,
            unfulfilled_threshold_hours=unfulfilled_threshold_hours,
            settlement_window_hours=settlement_window_hours,
            as_of=parsed_as_of,
        )
        return ExceptionDetectionRunResponse(
            success=True,
            message="Financial exception detection executed successfully.",
            **res,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Exception detection failed: {str(exc)}")


# ---------------------------------------------------------------------------
# Phase 2B: Central Financial Exceptions Investigation Workspace
# ---------------------------------------------------------------------------
@router.get("/cases", response_model=PaginatedFinancialExceptions, summary="List investigation cases")
def list_financial_exceptions(
    exception_type: Optional[str] = Query(None, description="Filter by type e.g. PAID_BUT_UNFULFILLED, SETTLEMENT_MISSING_IN_BANK"),
    risk_level: Optional[str] = Query(None, description="Filter by risk: CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, ASSIGNED, IN_REVIEW, RESOLVED, DISMISSED, ESCALATED"),
    suggested_owner: Optional[str] = Query(None, description="Filter by owner: Finance, Operations, Support"),
    search: Optional[str] = Query(None, description="Search case_id, explanation, order_id, payment_id, settlement_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lists central financial exception cases with multi-factor risk levels and owner assignments.
    """
    query = db.query(FinancialException)

    if exception_type:
        query = query.filter(FinancialException.exception_type == exception_type.upper().strip())
    if risk_level:
        query = query.filter(FinancialException.risk_level == risk_level.upper().strip())
    if status:
        query = query.filter(FinancialException.status == status.upper().strip())
    if suggested_owner:
        query = query.filter(FinancialException.suggested_owner.ilike(f"%{suggested_owner.strip()}%"))

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                FinancialException.case_id.ilike(s),
                FinancialException.explanation.ilike(s),
                FinancialException.related_order_id.ilike(s),
                FinancialException.related_payment_id.ilike(s),
                FinancialException.related_settlement_id.ilike(s),
                FinancialException.related_bank_entry_id.ilike(s),
            )
        )

    total = query.count()
    items = query.order_by(FinancialException.value_at_risk.desc(), FinancialException.detected_at.desc()).offset(offset).limit(limit).all()

    return PaginatedFinancialExceptions(
        total=total,
        items=items,
        limit=limit,
        offset=offset,
    )


@router.get("/cases/summary", response_model=FinancialExceptionsSummary, summary="Summary KPI breakdown of investigation cases")
def get_financial_exceptions_summary(db: Session = Depends(get_db)):
    """
    Provides high-level KPIs for investigation cases:
    Total Cases, Value at Risk, breakdown by Risk Level, Owner, and Status.
    """
    cases = db.query(FinancialException).all()
    
    by_type = {}
    by_owner = {}
    by_status = {}
    critical_c = 0
    high_c = 0
    med_c = 0
    low_c = 0
    total_var = 0

    for c in cases:
        total_var += c.value_at_risk
        by_type[c.exception_type] = by_type.get(c.exception_type, 0) + 1
        by_owner[c.suggested_owner] = by_owner.get(c.suggested_owner, 0) + 1
        by_status[c.status] = by_status.get(c.status, 0) + 1
        
        rl = (c.risk_level or "").upper()
        if rl == "CRITICAL":
            critical_c += 1
        elif rl == "HIGH":
            high_c += 1
        elif rl == "MEDIUM":
            med_c += 1
        else:
            low_c += 1

    return FinancialExceptionsSummary(
        total_cases=len(cases),
        critical_count=critical_c,
        high_count=high_c,
        medium_count=med_c,
        low_count=low_c,
        total_value_at_risk_paise=total_var,
        total_value_at_risk_inr=f"₹{total_var / 100.0:,.2f}",
        by_type=by_type,
        by_owner=by_owner,
        by_status=by_status,
    )


@router.get("/cases/{case_id}", response_model=FinancialExceptionResponse, summary="Get single exception case details")
def get_single_financial_case(case_id: str, db: Session = Depends(get_db)):
    """
    Get full drill-down case investigation details including verified explanation and structured evidence.
    """
    case = db.query(FinancialException).filter(FinancialException.case_id == case_id).first()
    if not case:
        try:
            case = db.query(FinancialException).filter(FinancialException.id == int(case_id)).first()
        except ValueError:
            pass
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return case


@router.patch("/cases/{case_id}/status", response_model=FinancialExceptionResponse, summary="Update exception status or assignee")
def update_case_status(
    case_id: str,
    payload: ExceptionStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates case resolution status, assignee, and notes.
    """
    case = db.query(FinancialException).filter(FinancialException.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    valid_statuses = {"OPEN", "ASSIGNED", "IN_REVIEW", "RESOLVED", "DISMISSED", "ESCALATED"}
    target_status = payload.status.upper().strip()
    if target_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {sorted(list(valid_statuses))}")

    old_status = case.status
    old_assignee = case.assignee

    case.status = target_status
    if payload.assignee is not None:
        case.assignee = payload.assignee.strip()
    if payload.resolution_notes is not None:
        case.resolution_notes = payload.resolution_notes.strip()
    case.updated_at = datetime.utcnow()

    # Determine event type for audit trail
    if target_status in {"RESOLVED", "DISMISSED"}:
        event_type = "RESOLUTION"
    elif target_status == "ESCALATED":
        event_type = "ESCALATION"
    elif payload.assignee is not None and payload.assignee.strip() != (old_assignee or ""):
        event_type = "ASSIGNMENT"
    else:
        event_type = "STATUS_CHANGE"

    # Build from/to audit values
    from_val: dict = {"status": old_status}
    to_val: dict = {"status": target_status}
    if payload.assignee is not None:
        from_val["assignee"] = old_assignee
        to_val["assignee"] = payload.assignee.strip()

    log_event(
        db=db,
        entity_type="EXCEPTION_CASE",
        entity_id=case.case_id,
        event_type=event_type,
        actor="user",
        from_value=from_val,
        to_value=to_val,
        notes=payload.resolution_notes,
    )

    db.commit()
    db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# Phase 1 Backward Compatibility Endpoints
# ---------------------------------------------------------------------------
@router.get("", response_model=PaginatedExceptions)
def list_exceptions(
    severity: Optional[str] = Query(None, description="Filter by severity: HIGH, MEDIUM, LOW"),
    exception_type: Optional[str] = Query(None, description="Filter by exception type"),
    search: Optional[str] = Query(None, description="Search by ID, reason, entity ID"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get paginated exceptions generated from reconciliation_results (Phase 1).
    """
    try:
        return get_exceptions_list(
            db=db,
            severity=severity,
            exception_type=exception_type,
            search=search,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exceptions: {str(exc)}",
        )


@router.get("/summary", response_model=ExceptionSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    """
    Get high-level exception breakdown by severity and exception type (Phase 1).
    """
    try:
        return get_exceptions_summary(db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exceptions summary: {str(exc)}",
        )


@router.get("/{exception_id}", response_model=ExceptionDetail)
def get_exception_detail(
    exception_id: str,
    db: Session = Depends(get_db),
):
    """
    Get drill-down investigation details for a specific reconciliation result exception (Phase 1).
    """
    exc = get_exception_by_id(db, exception_id)
    if not exc:
        raise HTTPException(
            status_code=404,
            detail=f"Exception '{exception_id}' not found.",
        )
    return exc
