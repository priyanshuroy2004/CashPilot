"""
Exceptions service for CASHpilot AI.
Deterministically generates and filters exception cases from reconciliation_results.
"""
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import ReconciliationResult
from app.schemas.exceptions import (
    ExceptionDetail,
    ExceptionSummaryResponse,
    PaginatedExceptions,
    MatchingMethodCheck,
)

# Configurable Severity Thresholds in paise
HIGH_SEVERITY_THRESHOLD_PAISE = 1_000_000   # > ₹10,000
MEDIUM_SEVERITY_THRESHOLD_PAISE = 200_000   # >= ₹2,000 and <= ₹10,000


def calculate_severity(amount_at_risk_paise: int) -> str:
    """
    Deterministic rule-based severity assignment.
    HIGH: > ₹10,000 (1,000,000 paise)
    MEDIUM: ₹2,000 to ₹10,000 (200,000 to 1,000,000 paise)
    LOW: < ₹2,000 (< 200,000 paise)
    """
    abs_amt = abs(amount_at_risk_paise)
    if abs_amt > HIGH_SEVERITY_THRESHOLD_PAISE:
        return "HIGH"
    elif abs_amt >= MEDIUM_SEVERITY_THRESHOLD_PAISE:
        return "MEDIUM"
    else:
        return "LOW"


def map_recon_to_exception(recon: ReconciliationResult) -> Optional[ExceptionDetail]:
    """
    Converts a ReconciliationResult row into a rich ExceptionDetail object if it represents an anomaly.
    Returns None if the record is fully MATCHED.
    """
    status = str(recon.status or "").upper()
    etype = str(recon.entity_type or "").upper()
    mtype = str(recon.match_type or "").upper()
    reason = str(recon.reason or "")

    # Fully matched records are not exceptions
    if status in ("MATCHED", "MATCHED_WITH_TOLERANCE"):
        return None

    # Map to standardized Phase 1 Exception Types
    exc_type = "UNSPECIFIED_ANOMALY"
    rec_action = "Review transaction details."

    if etype == "ORDER":
        if status == "PAYMENT_MISSING":
            exc_type = "PAYMENT_MISSING"
            amount_at_risk = abs(recon.expected_amount or 0)
            rec_action = "Verify if checkout was abandoned or if webhook event was dropped."
        elif status == "AMOUNT_MISMATCH":
            exc_type = "PAYMENT_AMOUNT_MISMATCH"
            amount_at_risk = abs(recon.difference or 0)
            rec_action = "Investigate undercharging / discount leak on payment gateway."
        elif status == "FAILED_PAYMENT":
            exc_type = "FAILED_PAYMENT"
            amount_at_risk = abs(recon.expected_amount or 0)
            rec_action = "Notify customer of failed attempt or trigger checkout retry sequence."
        elif status == "NEEDS_REVIEW":
            if "Multiple captured" in reason or "Duplicate" in reason:
                exc_type = "AMBIGUOUS_PAYMENT"
                amount_at_risk = abs(recon.difference if recon.difference != 0 else (recon.expected_amount or 0))
                rec_action = "Check payment gateway for accidental duplicate customer charge / refund."
            else:
                exc_type = "PAYMENT_PENDING"
                amount_at_risk = abs(recon.expected_amount or 0)
                rec_action = "Poll payment gateway status until webhook reaches final state."
        else:
            exc_type = "ORDER_ANOMALY"
            amount_at_risk = abs(recon.difference or recon.expected_amount or 0)

    elif etype == "PAYMENT":
        if status == "ORDER_MISSING":
            exc_type = "ORDER_MISSING"
            amount_at_risk = abs(recon.actual_amount or 0)
            rec_action = "Orphan payment captured: verify if order creation failed in ecommerce DB."
        else:
            exc_type = "PAYMENT_ANOMALY"
            amount_at_risk = abs(recon.actual_amount or 0)

    elif etype == "SETTLEMENT":
        if status == "PENDING_BANK_CREDIT":
            exc_type = "SETTLEMENT_MISSING_IN_BANK"
            amount_at_risk = abs(recon.expected_amount or 0)
            rec_action = "Contact payment gateway support to confirm UTR payout dispatch."
        elif status == "MISMATCH":
            exc_type = "SETTLEMENT_AMOUNT_MISMATCH"
            amount_at_risk = abs(recon.difference or 0)
            rec_action = "Audit fee and tax deductions with gateway settlement sheet."
        elif status == "NEEDS_REVIEW":
            exc_type = "AMBIGUOUS_BANK_MATCH"
            amount_at_risk = abs(recon.expected_amount or 0)
            rec_action = "Manual bank statement reconciliation required for multiple candidate payouts."
        else:
            exc_type = "SETTLEMENT_ANOMALY"
            amount_at_risk = abs(recon.difference or recon.expected_amount or 0)

    else:
        amount_at_risk = abs(recon.difference or recon.expected_amount or 0)

    severity = calculate_severity(amount_at_risk)

    # Build Attempted Methods Evidence Trail
    methods_attempted: List[MatchingMethodCheck] = []
    if etype == "SETTLEMENT":
        methods_attempted = [
            MatchingMethodCheck(
                method="Level 1: EXACT_UTR",
                attempted=True,
                passed=(mtype == "EXACT_UTR"),
                details="Checked bank statement for matching settlement UTR tracking code."
            ),
            MatchingMethodCheck(
                method="Level 2: REFERENCE_MATCH",
                attempted=True,
                passed=(mtype == "REFERENCE_MATCH"),
                details="Searched bank credit transaction narration text for Settlement ID."
            ),
            MatchingMethodCheck(
                method="Level 3: AMOUNT_DATE_MATCH",
                attempted=True,
                passed=(mtype == "AMOUNT_DATE_MATCH"),
                details="Searched within ±7 day window for net settlement amount matching bank credit."
            ),
        ]
    elif etype in ("ORDER", "PAYMENT"):
        methods_attempted = [
            MatchingMethodCheck(
                method="Level 1: EXACT_ORDER_ID",
                attempted=True,
                passed=(mtype == "EXACT_ORDER_ID"),
                details="Verified order_id in payment gateway records."
            ),
            MatchingMethodCheck(
                method="Level 2: AMOUNT_VALIDATION",
                attempted=(mtype == "EXACT_ORDER_ID"),
                passed=(status != "AMOUNT_MISMATCH"),
                details="Compared order gross amount with payment gateway captured amount."
            ),
            MatchingMethodCheck(
                method="Level 3: STATUS_VALIDATION",
                attempted=(mtype == "EXACT_ORDER_ID"),
                passed=(status not in ("FAILED_PAYMENT", "NEEDS_REVIEW")),
                details="Verified payment status is successfully captured without retry anomalies."
            ),
        ]

    return ExceptionDetail(
        id=recon.id,
        exception_id=f"EXC-{recon.id:04d}",
        exception_type=exc_type,
        entity_type=etype,
        entity_id=recon.entity_id,
        related_entity_id=recon.related_entity_id,
        amount_at_risk=amount_at_risk,
        severity=severity,
        status="OPEN",
        match_type=recon.match_type,
        confidence=float(recon.confidence) if recon.confidence is not None else None,
        expected_amount=recon.expected_amount,
        actual_amount=recon.actual_amount,
        difference=recon.difference,
        reason=reason,
        created_at=recon.created_at,
        methods_attempted=methods_attempted,
        recommended_action=rec_action,
    )


def get_exceptions_list(
    db: Session,
    severity: Optional[str] = None,
    exception_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedExceptions:
    """
    Fetches, filters, and paginates exceptions from reconciliation_results.
    """
    # Fetch non-matched reconciliation results
    query = db.query(ReconciliationResult).filter(
        ~ReconciliationResult.status.in_(["MATCHED", "MATCHED_WITH_TOLERANCE"])
    )

    all_raw = query.all()
    all_exceptions: List[ExceptionDetail] = []
    for r in all_raw:
        exc = map_recon_to_exception(r)
        if exc is not None:
            all_exceptions.append(exc)

    # Apply filters in Python memory (allows full computed field filtering)
    filtered = all_exceptions

    if severity:
        sev_upper = severity.upper()
        filtered = [e for e in filtered if e.severity == sev_upper]

    if exception_type:
        type_upper = exception_type.upper()
        filtered = [e for e in filtered if e.exception_type.upper() == type_upper]

    if search:
        s_lower = search.lower().strip()
        filtered = [
            e for e in filtered
            if (s_lower in e.exception_id.lower()
                or s_lower in e.entity_id.lower()
                or (e.related_entity_id and s_lower in e.related_entity_id.lower())
                or (e.reason and s_lower in e.reason.lower())
                or s_lower in e.exception_type.lower())
        ]

    # Sort by amount_at_risk descending (highest financial risk first)
    filtered.sort(key=lambda x: x.amount_at_risk, reverse=True)

    total = len(filtered)
    paged = filtered[offset : offset + limit]

    return PaginatedExceptions(
        total=total,
        items=paged,
        limit=limit,
        offset=offset,
    )


def get_exceptions_summary(db: Session) -> ExceptionSummaryResponse:
    """
    Computes summary metrics across all generated exceptions.
    """
    query = db.query(ReconciliationResult).filter(
        ~ReconciliationResult.status.in_(["MATCHED", "MATCHED_WITH_TOLERANCE"])
    )
    all_raw = query.all()

    high = 0
    medium = 0
    low = 0
    total_var = 0
    by_type: Dict[str, int] = {}

    for r in all_raw:
        exc = map_recon_to_exception(r)
        if exc is not None:
            total_var += exc.amount_at_risk
            if exc.severity == "HIGH":
                high += 1
            elif exc.severity == "MEDIUM":
                medium += 1
            else:
                low += 1

            by_type[exc.exception_type] = by_type.get(exc.exception_type, 0) + 1

    return ExceptionSummaryResponse(
        total_exceptions=len(all_raw),
        high_severity=high,
        medium_severity=medium,
        low_severity=low,
        total_value_at_risk=total_var,
        by_type=by_type,
    )


def get_exception_by_id(db: Session, exception_id: str) -> Optional[ExceptionDetail]:
    """
    Finds a single exception by either DB numeric ID or 'EXC-XXXX' string.
    """
    rec_id: Optional[int] = None
    if exception_id.startswith("EXC-"):
        try:
            rec_id = int(exception_id.replace("EXC-", ""))
        except ValueError:
            pass
    else:
        try:
            rec_id = int(exception_id)
        except ValueError:
            pass

    if rec_id is not None:
        recon = db.query(ReconciliationResult).filter(ReconciliationResult.id == rec_id).first()
        if recon:
            return map_recon_to_exception(recon)

    # Fallback search by entity_id
    recon = db.query(ReconciliationResult).filter(ReconciliationResult.entity_id == exception_id).first()
    if recon:
        return map_recon_to_exception(recon)

    return None
