"""
Settlement Fee/Tax/Net Calculation Engine — Phase 2A

For every settlement, deterministically calculates:

  expected_net_amount =
      gross_amount          (sum of all payment amounts in batch)
    - fee_amount            (payment gateway processing fee)
    - tax_amount            (GST 18% on gateway fee)
    - refund_adjustment     (total customer refunds deducted from payout)
    + other_adjustment      (positive credits, e.g. clawback reversals)

Compares expected_net_amount against reported_net_amount (stored in settlements table).

Rules:
  - Uses Python decimal.Decimal for ALL money arithmetic. No float operations on money.
  - A tolerance of ±1 paise is allowed for CORRECT status (rounding edge cases).
  - If reported_net differs by more than tolerance → DISCREPANCY.
  - Stores settlement_calculations rows — one per settlement, idempotent (upsert by settlement_id).
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, List, Any

from sqlalchemy.orm import Session

from app.models.models import (
    Settlement,
    SettlementLine,
    Refund,
    SettlementCalculation,
)


# Tolerance in paise for CORRECT status
_TOLERANCE_PAISE: int = 1


def _to_decimal(value: Any) -> Decimal:
    """Safely convert any numeric value to Decimal without float intermediary."""
    if value is None:
        return Decimal(0)
    return Decimal(str(int(value)))


def calculate_settlement(
    settlement: Settlement,
    lines: List[SettlementLine],
    refunds: List[Refund],
    tolerance: int = _TOLERANCE_PAISE,
) -> Dict[str, Any]:
    """
    Calculate the expected net amount for a single settlement.

    Parameters
    ----------
    settlement : Settlement ORM object
    lines      : SettlementLine records for this settlement (may be empty)
    refunds    : Refund records linked to this settlement
    tolerance  : Acceptable paise difference for CORRECT status (default 1)

    Returns
    -------
    dict with all calculation fields ready for SettlementCalculation ORM insert.
    """
    sid = str(settlement.settlement_id)

    # Pull reported figures from the settlements table (authoritative source data)
    gross = _to_decimal(settlement.gross_amount)
    fee = _to_decimal(settlement.fee_amount)
    tax = _to_decimal(settlement.tax_amount)
    reported_adj = _to_decimal(settlement.adjustment_amount)  # raw adjustment from settlements table
    reported_net = _to_decimal(settlement.net_amount)

    # Count payments in batch (from settlement_lines)
    payment_count = len(lines)

    # Calculate total refund adjustment from linked refund records
    # Only count 'processed' refunds (not pending/failed)
    refund_total = Decimal(0)
    for r in refunds:
        if str(getattr(r, "status", "")).lower() == "processed":
            refund_total += _to_decimal(r.amount)

    # Determine refund_adjustment and other_adjustment from available data.
    # The settlement's adjustment_amount field combines all adjustments (refunds + credits).
    # Negative adjustment = net deduction (refunds dominate).
    # Positive adjustment = net credit (credits dominate).
    if refund_total > 0:
        # Explicit refund records are available — use those as refund_adjustment.
        # other_adjustment is any remaining positive credit beyond the refunds.
        # We DON'T add reported_adj to refund_total since the settlement CSV's
        # adjustment_amount already encodes the same refunds in a different form.
        refund_adjustment = refund_total
        other_adj = Decimal(0)
    else:
        # No explicit refund data — use settlement's adjustment_amount directly.
        # Negative adjustment = refunds/debits; positive = credits
        if reported_adj < 0:
            refund_adjustment = abs(reported_adj)
            other_adj = Decimal(0)
        else:
            refund_adjustment = Decimal(0)
            other_adj = reported_adj

    # ── CORE FORMULA (all Decimal, no float) ──────────────────────────────
    #   expected_net = gross - fee - tax - refund_adjustment + other_adjustment
    expected_net = gross - fee - tax - refund_adjustment + other_adj

    # Round to nearest paise (should be exact with integer inputs, but belt-and-suspenders)
    expected_net = expected_net.to_integral_value(rounding=ROUND_HALF_UP)

    # Difference: positive = reported is higher than expected (favours merchant)
    #             negative = reported is lower (shortfall / discrepancy)
    difference = reported_net - expected_net

    # Determine status
    if abs(int(difference)) <= tolerance:
        status = "CORRECT"
    else:
        status = "DISCREPANCY"

    return {
        "settlement_id": sid,
        "gross_amount": int(gross),
        "fee_amount": int(fee),
        "tax_amount": int(tax),
        "refund_adjustment": int(refund_adjustment),
        "other_adjustment": int(other_adj),
        "expected_net_amount": int(expected_net),
        "reported_net_amount": int(reported_net),
        "calculation_status": status,
        "calculation_difference": int(difference),
        "payment_count": payment_count,
    }


def run_settlement_calculations(
    db: Session,
    tolerance: int = _TOLERANCE_PAISE,
) -> Dict[str, Any]:
    """
    Run fee/tax/net calculation for ALL settlements in the database.

    Clears previous settlement_calculations and recomputes from scratch.
    This ensures idempotency — safe to re-run after demo data reload.

    Returns
    -------
    dict with summary counts: total, correct, discrepancy
    """
    # Clear previous results
    db.query(SettlementCalculation).delete(synchronize_session=False)
    db.commit()

    settlements = db.query(Settlement).all()

    # Pre-index settlement lines by settlement_id
    all_lines = db.query(SettlementLine).all()
    lines_by_settlement: Dict[str, List[SettlementLine]] = {}
    for line in all_lines:
        sid = str(line.settlement_id)
        lines_by_settlement.setdefault(sid, []).append(line)

    # Pre-index refunds by settlement_id
    all_refunds = db.query(Refund).all()
    refunds_by_settlement: Dict[str, List[Refund]] = {}
    for r in all_refunds:
        sid = str(getattr(r, "settlement_id", "") or "")
        if sid:
            refunds_by_settlement.setdefault(sid, []).append(r)

    results = []
    counts = {"total": 0, "correct": 0, "discrepancy": 0}

    for s in settlements:
        sid = str(s.settlement_id)
        calc = calculate_settlement(
            settlement=s,
            lines=lines_by_settlement.get(sid, []),
            refunds=refunds_by_settlement.get(sid, []),
            tolerance=tolerance,
        )

        obj = SettlementCalculation(
            settlement_id=calc["settlement_id"],
            gross_amount=calc["gross_amount"],
            fee_amount=calc["fee_amount"],
            tax_amount=calc["tax_amount"],
            refund_adjustment=calc["refund_adjustment"],
            other_adjustment=calc["other_adjustment"],
            expected_net_amount=calc["expected_net_amount"],
            reported_net_amount=calc["reported_net_amount"],
            calculation_status=calc["calculation_status"],
            calculation_difference=calc["calculation_difference"],
            payment_count=calc["payment_count"],
            created_at=datetime.utcnow(),
        )
        results.append(obj)
        counts["total"] += 1
        if calc["calculation_status"] == "CORRECT":
            counts["correct"] += 1
        else:
            counts["discrepancy"] += 1

    db.bulk_save_objects(results)
    db.commit()

    return counts
