"""
Refund Reconciliation Engine — Phase 2A

Traces each refund through three layers:
  1. Payment gateway refund record (source of truth: refund_amount)
  2. Settlement adjustment (was refund deducted from the settlement payout?)
  3. Accounting ledger entry (was refund booked in accounting records?)

Possible statuses:
  REFUND_MATCHED                    — present in gateway + settlement + ledger, amounts consistent
  REFUND_MISSING_IN_LEDGER          — refund in gateway/settlement but no matching ledger REFUND entry
  REFUND_AMOUNT_MISMATCH            — ledger entry found but amount differs from gateway amount
  DUPLICATE_REFUND                  — same refund_id appears multiple times in ledger
  REFUND_PENDING                    — refund status is 'pending' (not yet processed)
  REFUND_SETTLEMENT_ADJUSTMENT_MISSING — refund processed but not linked to any settlement

Rules:
  - Uses deterministic matching only. No fuzzy guessing.
  - A refund is DUPLICATE if the same refund_id maps to >1 ledger REFUND entries.
  - Tolerance: ±1 paise for amount comparison.
  - PENDING refunds skip ledger validation entirely.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Refund,
    LedgerEntry,
    RefundReconciliationResult,
)

_TOLERANCE_PAISE: int = 1


def _classify_refund(
    refund: Refund,
    ledger_entries_for_refund: List[LedgerEntry],
) -> Dict[str, Any]:
    """
    Classify a single refund against its matching ledger entries.

    Parameters
    ----------
    refund                    : Refund ORM object
    ledger_entries_for_refund : LedgerEntry rows where reference_id == refund.refund_id
                                AND entry_type == 'REFUND'

    Returns
    -------
    dict with all RefundReconciliationResult fields (excluding id/created_at)
    """
    refund_id = str(refund.refund_id)
    payment_id = str(getattr(refund, "payment_id", "") or "")
    order_id = str(getattr(refund, "order_id", "") or "")
    settlement_id = str(getattr(refund, "settlement_id", "") or "") or None
    gateway_amount = int(refund.amount or 0)
    status_raw = str(getattr(refund, "status", "")).lower()

    # ── PENDING: skip ledger validation ──────────────────────────────────────
    if status_raw == "pending":
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": settlement_id,
            "ledger_entry_id": None,
            "refund_amount": gateway_amount,
            "ledger_amount": None,
            "amount_difference": None,
            "refund_status": "REFUND_PENDING",
            "duplicate_count": 0,
            "notes": f"Refund {refund_id} is pending — ledger validation deferred until processing completes.",
        }

    # ── SETTLEMENT ADJUSTMENT MISSING ────────────────────────────────────────
    if not settlement_id:
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": None,
            "ledger_entry_id": None,
            "refund_amount": gateway_amount,
            "ledger_amount": None,
            "amount_difference": None,
            "refund_status": "REFUND_SETTLEMENT_ADJUSTMENT_MISSING",
            "duplicate_count": 0,
            "notes": f"Refund {refund_id} (processed) has no linked settlement_id. Settlement adjustment is missing.",
        }

    # Filter to REFUND-type ledger entries for this refund_id
    refund_entries = [
        e for e in ledger_entries_for_refund
        if str(e.entry_type).upper() == "REFUND"
    ]

    # ── MISSING IN LEDGER ─────────────────────────────────────────────────────
    if not refund_entries:
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": settlement_id,
            "ledger_entry_id": None,
            "refund_amount": gateway_amount,
            "ledger_amount": None,
            "amount_difference": None,
            "refund_status": "REFUND_MISSING_IN_LEDGER",
            "duplicate_count": 0,
            "notes": f"Refund {refund_id} of {gateway_amount} paise exists in gateway but no REFUND ledger entry found.",
        }

    # ── DUPLICATE CHECK ───────────────────────────────────────────────────────
    if len(refund_entries) > 1:
        total_ledger = sum(int(e.amount) for e in refund_entries)
        ids = ", ".join(str(e.entry_id) for e in refund_entries)
        diff = total_ledger - gateway_amount
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": settlement_id,
            "ledger_entry_id": ids,
            "refund_amount": gateway_amount,
            "ledger_amount": total_ledger,
            "amount_difference": diff,
            "refund_status": "DUPLICATE_REFUND",
            "duplicate_count": len(refund_entries),
            "notes": (
                f"Found {len(refund_entries)} REFUND ledger entries for {refund_id} ({ids}). "
                f"Total ledger amount {total_ledger} paise vs gateway {gateway_amount} paise."
            ),
        }

    # ── SINGLE ENTRY: AMOUNT CHECK ────────────────────────────────────────────
    entry = refund_entries[0]
    ledger_amount = int(entry.amount)
    diff = ledger_amount - gateway_amount

    if abs(diff) <= _TOLERANCE_PAISE:
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": settlement_id,
            "ledger_entry_id": str(entry.entry_id),
            "refund_amount": gateway_amount,
            "ledger_amount": ledger_amount,
            "amount_difference": diff,
            "refund_status": "REFUND_MATCHED",
            "duplicate_count": 0,
            "notes": f"Refund {refund_id} matched ledger entry {entry.entry_id}" + (
                f" (within {diff} paise tolerance)" if diff != 0 else ""
            ),
        }
    else:
        return {
            "refund_id": refund_id,
            "payment_id": payment_id,
            "order_id": order_id,
            "settlement_id": settlement_id,
            "ledger_entry_id": str(entry.entry_id),
            "refund_amount": gateway_amount,
            "ledger_amount": ledger_amount,
            "amount_difference": diff,
            "refund_status": "REFUND_AMOUNT_MISMATCH",
            "duplicate_count": 0,
            "notes": (
                f"Refund {refund_id}: gateway amount {gateway_amount} paise, "
                f"ledger amount {ledger_amount} paise, difference {diff} paise."
            ),
        }


def run_refund_matching(db: Session) -> Dict[str, Any]:
    """
    Run refund reconciliation for ALL refunds in the database.

    Clears previous refund_reconciliation_results and recomputes from scratch.

    Returns
    -------
    dict with total count and breakdown by refund_status
    """
    # Clear previous results
    db.query(RefundReconciliationResult).delete(synchronize_session=False)
    db.commit()

    refunds = db.query(Refund).all()

    # Pre-index ledger entries by reference_id (only REFUND type needed here)
    all_refund_ledger = db.query(LedgerEntry).filter(
        LedgerEntry.entry_type == "REFUND"
    ).all()
    ledger_by_refund_id: Dict[str, List[LedgerEntry]] = {}
    for entry in all_refund_ledger:
        ref = str(entry.reference_id or "")
        ledger_by_refund_id.setdefault(ref, []).append(entry)

    results = []
    status_counts: Dict[str, int] = {}

    for r in refunds:
        rid = str(r.refund_id)
        ledger_entries_for_this = ledger_by_refund_id.get(rid, [])
        classification = _classify_refund(r, ledger_entries_for_this)

        status = classification["refund_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

        row = RefundReconciliationResult(
            refund_id=classification["refund_id"],
            payment_id=classification["payment_id"],
            order_id=classification["order_id"],
            settlement_id=classification["settlement_id"],
            ledger_entry_id=classification["ledger_entry_id"],
            refund_amount=classification["refund_amount"],
            ledger_amount=classification["ledger_amount"],
            amount_difference=classification["amount_difference"],
            refund_status=classification["refund_status"],
            duplicate_count=classification["duplicate_count"],
            notes=classification["notes"],
            created_at=datetime.utcnow(),
        )
        results.append(row)

    db.bulk_save_objects(results)
    db.commit()

    return {
        "total_refunds": len(refunds),
        "by_status": status_counts,
    }
