"""
Order ↔ Payment deterministic reconciliation module.

Prioritizes financial correctness over match rate.
All amounts are handled in integer paise.
Zero external AI/LLM dependencies.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ReconItem:
    entity_type: str           # ORDER | PAYMENT | SETTLEMENT | BANK_TRANSACTION
    entity_id: str             # primary key / identifier of entity
    related_entity_id: Optional[str] = None
    match_type: Optional[str] = None       # EXACT_ORDER_ID | UNMATCHED | AMBIGUOUS | etc.
    status: str = "NEEDS_REVIEW"           # MATCHED | AMOUNT_MISMATCH | PAYMENT_MISSING | ORDER_MISSING | FAILED_PAYMENT | NEEDS_REVIEW
    confidence: float = 100.0
    expected_amount: Optional[int] = None  # paise
    actual_amount: Optional[int] = None    # paise
    difference: Optional[int] = None       # paise (actual - expected)
    reason: Optional[str] = None


def reconcile_orders_payments(
    orders: List[Any],
    payments: List[Any],
    tolerance: int = 0,
) -> List[ReconItem]:
    """
    Reconcile a list of Order objects against a list of Payment objects.

    Rules:
    - Primary link: payment.order_id == order.order_id
    - Captured payment + matching order + matching amount -> MATCHED
    - Captured payment + matching order + different amount -> AMOUNT_MISMATCH
    - Order without payment -> PAYMENT_MISSING
    - Payment without order -> ORDER_MISSING
    - Payment status failed (no captured payment) -> FAILED_PAYMENT
    - Multiple captured payments or ambiguous relationship -> NEEDS_REVIEW
    """
    results: List[ReconItem] = []

    # Map orders by order_id
    order_map: Dict[str, Any] = {}
    for o in orders:
        oid = str(getattr(o, "order_id", "") or "")
        if oid:
            order_map[oid] = o

    # Group payments by order_id
    payments_by_order: Dict[str, List[Any]] = defaultdict(list)
    orphan_payments: List[Any] = []

    for p in payments:
        p_oid = str(getattr(p, "order_id", "") or "")
        if p_oid and p_oid in order_map:
            payments_by_order[p_oid].append(p)
        else:
            orphan_payments.append(p)

    # 1. Process all Orders
    for oid, order in order_map.items():
        order_amount = int(getattr(order, "order_amount", 0) or 0)
        p_list = payments_by_order.get(oid, [])

        if not p_list:
            # Order with zero payments
            results.append(
                ReconItem(
                    entity_type="ORDER",
                    entity_id=oid,
                    related_entity_id=None,
                    match_type="UNMATCHED",
                    status="PAYMENT_MISSING",
                    confidence=0.0,
                    expected_amount=order_amount,
                    actual_amount=0,
                    difference=-order_amount,
                    reason="No payment record found for this order",
                )
            )
            continue

        captured_payments = [
            p for p in p_list if str(getattr(p, "status", "")).lower() == "captured"
        ]
        failed_payments = [
            p for p in p_list if str(getattr(p, "status", "")).lower() == "failed"
        ]

        if len(p_list) == 1:
            payment = p_list[0]
            pid = str(getattr(payment, "payment_id", "") or "")
            p_status = str(getattr(payment, "status", "")).lower()
            p_amount = int(getattr(payment, "amount", 0) or 0)
            diff = p_amount - order_amount

            if p_status == "captured":
                if abs(diff) <= tolerance:
                    results.append(
                        ReconItem(
                            entity_type="ORDER",
                            entity_id=oid,
                            related_entity_id=pid,
                            match_type="EXACT_ORDER_ID",
                            status="MATCHED",
                            confidence=100.0,
                            expected_amount=order_amount,
                            actual_amount=p_amount,
                            difference=diff,
                            reason="Order ID and captured payment amount matched",
                        )
                    )
                else:
                    results.append(
                        ReconItem(
                            entity_type="ORDER",
                            entity_id=oid,
                            related_entity_id=pid,
                            match_type="EXACT_ORDER_ID",
                            status="AMOUNT_MISMATCH",
                            confidence=100.0,
                            expected_amount=order_amount,
                            actual_amount=p_amount,
                            difference=diff,
                            reason=f"Payment amount ({p_amount} paise) differs from order ({order_amount} paise) by {diff} paise",
                        )
                    )
            elif p_status == "failed":
                results.append(
                    ReconItem(
                        entity_type="ORDER",
                        entity_id=oid,
                        related_entity_id=pid,
                        match_type="EXACT_ORDER_ID",
                        status="FAILED_PAYMENT",
                        confidence=100.0,
                        expected_amount=order_amount,
                        actual_amount=0,
                        difference=-order_amount,
                        reason=f"Payment {pid} failed",
                    )
                )
            else:
                # Pending or other status
                results.append(
                    ReconItem(
                        entity_type="ORDER",
                        entity_id=oid,
                        related_entity_id=pid,
                        match_type="EXACT_ORDER_ID",
                        status="NEEDS_REVIEW",
                        confidence=80.0,
                        expected_amount=order_amount,
                        actual_amount=p_amount,
                        difference=diff,
                        reason=f"Payment {pid} in non-final status '{p_status}'",
                    )
                )
        else:
            # Multiple payments for same order (e.g. retry / duplicate / ambiguous)
            if len(captured_payments) == 1 and len(failed_payments) >= 1:
                # One retry succeeded, prior attempt(s) failed
                captured_p = captured_payments[0]
                pid = str(getattr(captured_p, "payment_id", "") or "")
                p_amount = int(getattr(captured_p, "amount", 0) or 0)
                diff = p_amount - order_amount
                failed_ids = [str(getattr(p, "payment_id", "")) for p in failed_payments]

                results.append(
                    ReconItem(
                        entity_type="ORDER",
                        entity_id=oid,
                        related_entity_id=pid,
                        match_type="EXACT_ORDER_ID",
                        status="NEEDS_REVIEW",
                        confidence=90.0,
                        expected_amount=order_amount,
                        actual_amount=p_amount,
                        difference=diff,
                        reason=f"Duplicate payment attempts: captured payment {pid} with {len(failed_payments)} failed attempt(s) ({', '.join(failed_ids)})",
                    )
                )
            elif len(captured_payments) > 1:
                # Multiple captured payments! Definite ambiguity / overpayment risk
                cap_ids = [str(getattr(p, "payment_id", "")) for p in captured_payments]
                total_captured = sum(int(getattr(p, "amount", 0) or 0) for p in captured_payments)
                results.append(
                    ReconItem(
                        entity_type="ORDER",
                        entity_id=oid,
                        related_entity_id=",".join(cap_ids),
                        match_type="AMBIGUOUS_PAYMENTS",
                        status="NEEDS_REVIEW",
                        confidence=60.0,
                        expected_amount=order_amount,
                        actual_amount=total_captured,
                        difference=total_captured - order_amount,
                        reason=f"Multiple captured payments ({len(captured_payments)}) found for order: {', '.join(cap_ids)}",
                    )
                )
            else:
                # Multiple payments, all failed
                all_ids = [str(getattr(p, "payment_id", "")) for p in p_list]
                results.append(
                    ReconItem(
                        entity_type="ORDER",
                        entity_id=oid,
                        related_entity_id=",".join(all_ids),
                        match_type="EXACT_ORDER_ID",
                        status="FAILED_PAYMENT",
                        confidence=100.0,
                        expected_amount=order_amount,
                        actual_amount=0,
                        difference=-order_amount,
                        reason=f"All {len(p_list)} payment attempts failed ({', '.join(all_ids)})",
                    )
                )

    # 2. Process Orphan Payments (payments without valid matching order)
    for p in orphan_payments:
        pid = str(getattr(p, "payment_id", "") or "")
        p_amount = int(getattr(p, "amount", 0) or 0)
        p_oid = str(getattr(p, "order_id", "") or "")

        results.append(
            ReconItem(
                entity_type="PAYMENT",
                entity_id=pid,
                related_entity_id=p_oid if p_oid else None,
                match_type="UNMATCHED",
                status="ORDER_MISSING",
                confidence=0.0,
                expected_amount=0,
                actual_amount=p_amount,
                difference=p_amount,
                reason=f"Payment {pid} has no matching order record in database" + (f" (referenced non-existent order '{p_oid}')" if p_oid else ""),
            )
        )

    return results
