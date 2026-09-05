"""
Tax-Line Matching Engine — Phase 2A

Validates each settlement's financial components against the accounting ledger.

For every settlement, checks five components:
  FEE    → ledger must have a FEE_EXPENSE entry for this settlement_id
  TAX    → ledger must have a TAX entry for this settlement_id
  REFUND → ledger must have REFUND entries summing to settlement refund_adjustment
  NET    → ledger must have a BANK_CREDIT entry matching settlement net_amount

Possible statuses per component:
  MATCHED              — settlement value == ledger value (within 1 paise tolerance)
  MISSING_LEDGER_ENTRY — settlement has a non-zero value, no ledger entry found
  AMOUNT_MISMATCH      — ledger entry found but amount differs beyond tolerance
  DUPLICATE_ENTRY      — multiple ledger entries found for same component
  PENDING_REVIEW       — ambiguous situation requiring human review

The tax matcher NEVER invents missing data. It only reports what it can determine.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Settlement,
    LedgerEntry,
    TaxReconciliationResult,
    Refund,
)

_TOLERANCE_PAISE: int = 1


def _match_component(
    settlement_id: str,
    component: str,
    expected_amount: int,
    ledger_entries: List[LedgerEntry],
) -> Dict[str, Any]:
    """
    Compare a single settlement component against matching ledger entries.

    Parameters
    ----------
    settlement_id   : The settlement being validated
    component       : One of FEE | TAX | REFUND | NET
    expected_amount : Amount from settlement record (paise)
    ledger_entries  : All ledger entries for this settlement_id + component type

    Returns
    -------
    dict with status, ledger_amount, difference, ledger_entry_id, notes
    """
    entry_type_map = {
        "FEE": "FEE_EXPENSE",
        "TAX": "TAX",
        "REFUND": "REFUND",
        "NET": "BANK_CREDIT",
    }
    required_type = entry_type_map.get(component, component)

    # Filter entries matching component type
    matching = [e for e in ledger_entries if str(e.entry_type).upper() == required_type]

    if not matching:
        if expected_amount == 0:
            # No ledger entry and no expected amount → nothing to validate
            return {
                "status": "MATCHED",
                "ledger_amount": 0,
                "difference": 0,
                "ledger_entry_id": None,
                "notes": f"{component} is zero — no ledger entry expected or required",
            }
        else:
            return {
                "status": "MISSING_LEDGER_ENTRY",
                "ledger_amount": None,
                "difference": None,
                "ledger_entry_id": None,
                "notes": f"No {required_type} ledger entry found for settlement {settlement_id}. Expected {expected_amount} paise.",
            }

    if len(matching) > 1 and component != "REFUND":
        # Duplicate (non-refund entries should be singular)
        total_ledger = sum(int(e.amount) for e in matching)
        ids = ", ".join(str(e.entry_id) for e in matching)
        return {
            "status": "DUPLICATE_ENTRY",
            "ledger_amount": total_ledger,
            "difference": total_ledger - expected_amount,
            "ledger_entry_id": ids,
            "notes": f"Found {len(matching)} duplicate {required_type} entries ({ids}). Expected exactly 1.",
        }

    # Sum ledger amounts (for REFUND component, multiple entries are normal)
    ledger_total = sum(int(e.amount) for e in matching)
    primary_entry = matching[0]
    entry_ids = ", ".join(str(e.entry_id) for e in matching)

    diff = ledger_total - expected_amount

    if abs(diff) <= _TOLERANCE_PAISE:
        return {
            "status": "MATCHED",
            "ledger_amount": ledger_total,
            "difference": diff,
            "ledger_entry_id": entry_ids,
            "notes": f"{component} matches ledger entry {entry_ids}" + (f" (within {diff} paise tolerance)" if diff != 0 else ""),
        }
    else:
        return {
            "status": "AMOUNT_MISMATCH",
            "ledger_amount": ledger_total,
            "difference": diff,
            "ledger_entry_id": entry_ids,
            "notes": f"{component} mismatch: expected {expected_amount} paise, ledger shows {ledger_total} paise (diff={diff} paise)",
        }


def run_tax_matching(db: Session) -> Dict[str, Any]:
    """
    Run tax-line matching for ALL settlements.

    Clears previous tax_reconciliation_results and recomputes from scratch.

    Returns summary counts by status.
    """
    # Clear previous results
    db.query(TaxReconciliationResult).delete(synchronize_session=False)
    db.commit()

    settlements = db.query(Settlement).all()

    # Pre-index all ledger entries by reference_id
    all_ledger = db.query(LedgerEntry).all()
    ledger_by_ref: Dict[str, List[LedgerEntry]] = {}
    for entry in all_ledger:
        ref = str(entry.reference_id or "")
        ledger_by_ref.setdefault(ref, []).append(entry)

    # Pre-index refunds by settlement_id for REFUND component
    all_refunds = db.query(Refund).filter(Refund.status == "processed").all()
    refunds_by_settlement: Dict[str, List[Refund]] = {}
    for r in all_refunds:
        sid = str(getattr(r, "settlement_id", "") or "")
        if sid:
            refunds_by_settlement.setdefault(sid, []).append(r)

    results = []
    status_counts: Dict[str, int] = {}

    components_to_check = ["FEE", "TAX", "REFUND", "NET"]

    for s in settlements:
        sid = str(s.settlement_id)
        ledger_for_settlement = ledger_by_ref.get(sid, [])

        fee_expected = int(s.fee_amount or 0)
        tax_expected = int(s.tax_amount or 0)
        net_expected = int(s.net_amount or 0)

        # Refund adjustment: if we have explicit refunds, use those; else use adjustment_amount
        refunds_for_s = refunds_by_settlement.get(sid, [])
        if refunds_for_s:
            refund_expected = sum(int(r.amount) for r in refunds_for_s)
        else:
            adj = int(s.adjustment_amount or 0)
            refund_expected = abs(adj) if adj < 0 else 0

        component_values = {
            "FEE": fee_expected,
            "TAX": tax_expected,
            "REFUND": refund_expected,
            "NET": net_expected,
        }

        for comp in components_to_check:
            expected = component_values[comp]
            match_result = _match_component(
                settlement_id=sid,
                component=comp,
                expected_amount=expected,
                ledger_entries=ledger_for_settlement,
            )

            status = match_result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            row = TaxReconciliationResult(
                settlement_id=sid,
                component=comp,
                expected_amount=expected,
                ledger_amount=match_result["ledger_amount"],
                difference=match_result["difference"],
                status=status,
                ledger_entry_id=match_result["ledger_entry_id"],
                notes=match_result["notes"],
                created_at=datetime.utcnow(),
            )
            results.append(row)

    db.bulk_save_objects(results)
    db.commit()

    total = sum(status_counts.values())
    return {
        "total_checks": total,
        "settlements_checked": len(settlements),
        "by_status": status_counts,
    }
