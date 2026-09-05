"""
Deterministic Detection Engines for Financial Exceptions.

Implements:
  1. PAID_BUT_UNFULFILLED: Captured payments with no shipment after threshold.
  2. SETTLEMENT_MISSING_IN_BANK: Settlements past bank-credit window without credit verification.
  3. INGEST_OTHER_ANOMALIES: Bridge high-impact reconciliation & calculation discrepancies into central cases.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Order,
    Payment,
    Settlement,
    SettlementLine,
    BankTransaction,
    Shipment,
    ReconciliationResult,
    SettlementCalculation,
    RefundReconciliationResult,
    FinancialException,
)
from app.services.exceptions.prioritizer import calculate_exception_priority


def _paise_to_inr_str(paise: int) -> str:
    """Formats paise as INR string."""
    amt = paise / 100.0
    return f"₹{amt:,.2f}"


def get_evaluation_reference_time(
    db: Session,
    entity_type: str = "payment",
    user_as_of: Optional[datetime] = None,
) -> datetime:
    """
    Returns deterministic evaluation reference timestamp.
    For payments: defaults to max payment_captured_at in database.
    For settlements: defaults to max settlement_date in database.
    """
    if user_as_of:
        return user_as_of
    
    if entity_type == "payment":
        max_pay = db.query(func.max(Payment.payment_captured_at)).scalar()
        if max_pay:
            return max_pay
    elif entity_type == "settlement":
        max_setl = db.query(func.max(Settlement.settlement_date)).scalar()
        if max_setl:
            return max_setl

    # General fallback
    max_all = [
        d for d in [
            db.query(func.max(Payment.payment_captured_at)).scalar(),
            db.query(func.max(Settlement.settlement_date)).scalar(),
        ] if d is not None
    ]
    if max_all:
        return max(max_all)
    return datetime.utcnow()


def detect_paid_but_unfulfilled(
    db: Session,
    threshold_hours: float = 72.0,
    as_of: Optional[datetime] = None,
) -> List[FinancialException]:
    """
    Detects orders where payment was captured successfully, but no shipment confirmation
    exists after threshold_hours.
    """
    ref_time = get_evaluation_reference_time(db, entity_type="payment", user_as_of=as_of)
    exceptions: List[FinancialException] = []

    # 1. Query all successfully captured payments
    captured_payments = (
        db.query(Payment)
        .filter(Payment.status == "captured", Payment.payment_captured_at.isnot(None))
        .all()
    )

    # 2. Pre-fetch all shipped order_ids for fast O(1) lookup
    shipped_order_ids = set(
        db.query(Shipment.order_id)
        .filter(Shipment.status.in_(["DELIVERED", "IN_TRANSIT", "SHIPPED"]))
        .distinct()
        .all()
    )
    shipped_order_ids = {oid[0] for oid in shipped_order_ids}

    case_counter = 1

    for payment in captured_payments:
        order_id = payment.order_id
        if not order_id:
            continue

        # If shipment exists, fulfillment is satisfied
        if order_id in shipped_order_ids:
            continue

        # Calculate elapsed hours since payment capture
        elapsed_seconds = (ref_time - payment.payment_captured_at).total_seconds()
        elapsed_hours = max(0.0, elapsed_seconds / 3600.0)

        # Skip if within normal fulfillment threshold
        if elapsed_hours <= threshold_hours:
            continue

        # Look up order details
        order = db.query(Order).filter(Order.order_id == order_id).first()
        order_amount = order.order_amount if order else payment.amount

        # Look up downstream settlement and bank matching
        settlement_line = (
            db.query(SettlementLine)
            .filter(SettlementLine.payment_id == payment.payment_id)
            .first()
        )
        settlement_id = settlement_line.settlement_id if settlement_line else None
        
        bank_entry_id = None
        bank_utr = None
        if settlement_id:
            settlement = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
            if settlement:
                bank_utr = settlement.settlement_utr
                bank_recon = (
                    db.query(ReconciliationResult)
                    .filter(
                        ReconciliationResult.entity_type == "SETTLEMENT",
                        ReconciliationResult.entity_id == settlement_id,
                        ReconciliationResult.status == "MATCHED",
                    )
                    .first()
                )
                if bank_recon:
                    bank_entry_id = bank_recon.related_entity_id

        # Determine risk level & score
        risk_level, score = calculate_exception_priority(
            value_at_risk_paise=order_amount,
            elapsed_hours=elapsed_hours,
            exception_type="PAID_BUT_UNFULFILLED",
            has_customer_complaint=(elapsed_hours > 120),
        )

        inr_str = _paise_to_inr_str(order_amount)
        hours_str = f"{elapsed_hours:.1f}"

        # Verified deterministic explanation
        explanation = (
            f"Payment {payment.payment_id} for order {order_id} was captured successfully {hours_str} hours ago "
            f"({payment.payment_captured_at.strftime('%Y-%m-%d %H:%M')}). "
        )
        if settlement_id:
            explanation += f"The payment was included in settlement {settlement_id} "
            if bank_entry_id:
                explanation += f"and matched to bank credit {bank_entry_id}. "
            else:
                explanation += f"(payout in progress). "
        else:
            explanation += "The payment is pending batch settlement. "

        explanation += (
            f"However, no shipment record has been found in the logistics system. "
            f"The order value of {inr_str} is therefore flagged as an operational failure, "
            f"representing high customer dispute, chargeback, and refund risk."
        )

        triggering_rule = (
            f"PAID_BUT_UNFULFILLED_RULE: Payment captured > {threshold_hours:.0f}h ago "
            f"({hours_str}h elapsed) with no fulfillment confirmation in logistics records."
        )

        evidence = {
            "order_id": order_id,
            "order_amount_paise": order_amount,
            "order_amount_inr": inr_str,
            "payment_id": payment.payment_id,
            "payment_captured_at": payment.payment_captured_at.strftime("%Y-%m-%d %H:%M:%S"),
            "hours_since_payment": round(elapsed_hours, 1),
            "threshold_hours": threshold_hours,
            "settlement_id": settlement_id,
            "bank_entry_id": bank_entry_id,
            "bank_utr": bank_utr,
            "shipment_status": "MISSING",
            "risk_score": score,
            "risk_factors": [
                "unfulfilled_customer_order",
                "potential_customer_dispute",
                "chargeback_exposure",
                "refund_liability",
            ],
        }

        case_id = f"CASE-FUL-{order_id.replace('ORD-', '')}"

        exceptions.append(
            FinancialException(
                case_id=case_id,
                exception_type="PAID_BUT_UNFULFILLED",
                risk_level=risk_level,
                value_at_risk=order_amount,
                status="OPEN",
                suggested_owner="Operations",
                related_order_id=order_id,
                related_payment_id=payment.payment_id,
                related_settlement_id=settlement_id,
                related_bank_entry_id=bank_entry_id,
                evidence=evidence,
                explanation=explanation,
                triggering_rule=triggering_rule,
                detected_at=datetime.utcnow(),
            )
        )
        case_counter += 1

    return exceptions


def detect_settlement_missing_in_bank(
    db: Session,
    window_hours: float = 48.0,
    as_of: Optional[datetime] = None,
) -> List[FinancialException]:
    """
    Detects settlements where expected bank-credit window has passed without verified credit.
    Distinguishes normal timing delays (PENDING_EXPECTED_SETTLEMENT) from true cash leaks (SETTLEMENT_MISSING_IN_BANK).
    """
    ref_time = get_evaluation_reference_time(db, entity_type="settlement", user_as_of=as_of)
    exceptions: List[FinancialException] = []

    # 1. Query all settlements flagged as PENDING_BANK_CREDIT in Phase 1 reconciliation
    pending_recons = (
        db.query(ReconciliationResult)
        .filter(
            ReconciliationResult.entity_type == "SETTLEMENT",
            ReconciliationResult.status == "PENDING_BANK_CREDIT",
        )
        .all()
    )

    for recon in pending_recons:
        settlement_id = recon.entity_id
        settlement = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
        if not settlement or not settlement.settlement_date:
            continue

        # Calculate elapsed hours since settlement dispatch
        elapsed_seconds = (ref_time - settlement.settlement_date).total_seconds()
        elapsed_hours = max(0.0, elapsed_seconds / 3600.0)

        # If within expected bank window, this is normal timing delay (PENDING_EXPECTED_SETTLEMENT)
        if elapsed_hours <= window_hours:
            continue

        # Outside window: flag as SETTLEMENT_MISSING_IN_BANK
        expected_net = settlement.net_amount
        inr_str = _paise_to_inr_str(expected_net)
        hours_str = f"{elapsed_hours:.1f}"

        risk_level, score = calculate_exception_priority(
            value_at_risk_paise=expected_net,
            elapsed_hours=elapsed_hours,
            exception_type="SETTLEMENT_MISSING_IN_BANK",
            has_customer_complaint=False,
        )

        explanation = (
            f"Settlement {settlement_id} for {inr_str} was dispatched on "
            f"{settlement.settlement_date.strftime('%Y-%m-%d %H:%M')} ({hours_str} hours ago). "
            f"The standard bank-credit processing window of {window_hours:.0f} hours has elapsed, "
            f"but no matching credit has been detected in bank statements (UTR: {settlement.settlement_utr or 'N/A'}). "
            f"This represents an uncredited payout and direct cash-flow leakage risk."
        )

        triggering_rule = (
            f"SETTLEMENT_MISSING_IN_BANK_RULE: Settlement unreconciled after expected bank-credit window "
            f"of {window_hours:.0f}h ({hours_str}h elapsed since settlement dispatch)."
        )

        evidence = {
            "settlement_id": settlement_id,
            "settlement_date": settlement.settlement_date.strftime("%Y-%m-%d %H:%M:%S"),
            "expected_net_paise": expected_net,
            "expected_net_inr": inr_str,
            "settlement_utr": settlement.settlement_utr,
            "hours_since_settlement": round(elapsed_hours, 1),
            "window_hours": window_hours,
            "bank_reconciliation_status": "PENDING_BANK_CREDIT",
            "risk_score": score,
            "risk_factors": [
                "uncredited_gateway_payout",
                "bank_float_delay",
                "missing_settlement_utr",
                "cash_leakage_risk",
            ],
        }

        case_id = f"CASE-SETL-{settlement_id.replace('SETL-', '')}"

        exceptions.append(
            FinancialException(
                case_id=case_id,
                exception_type="SETTLEMENT_MISSING_IN_BANK",
                risk_level=risk_level,
                value_at_risk=expected_net,
                status="OPEN",
                suggested_owner="Finance",
                related_order_id=None,
                related_payment_id=None,
                related_settlement_id=settlement_id,
                related_bank_entry_id=None,
                evidence=evidence,
                explanation=explanation,
                triggering_rule=triggering_rule,
                detected_at=datetime.utcnow(),
            )
        )

    return exceptions


def ingest_reconciliation_exceptions(db: Session) -> List[FinancialException]:
    """
    Bridges high-impact Phase 1 and Phase 2A financial anomalies into central exceptions:
      - PAYMENT_AMOUNT_MISMATCH (order amount != payment amount)
      - CALCULATION_DISCREPANCY (reported net != calculated net)
      - REFUND_MISSING_IN_LEDGER (refund in gateway not posted to accounting books)
    """
    exceptions: List[FinancialException] = []

    # 1. Order/Payment Amount Mismatches from Phase 1
    amt_mismatches = (
        db.query(ReconciliationResult)
        .filter(
            ReconciliationResult.entity_type == "ORDER",
            ReconciliationResult.status == "AMOUNT_MISMATCH",
        )
        .all()
    )
    for recon in amt_mismatches:
        diff = abs(recon.difference or 0)
        risk_level, score = calculate_exception_priority(diff, 48.0, "PAYMENT_AMOUNT_MISMATCH")
        inr_diff = _paise_to_inr_str(diff)

        explanation = (
            f"Order {recon.entity_id} was billed for {_paise_to_inr_str(recon.expected_amount or 0)}, "
            f"but payment gateway captured {_paise_to_inr_str(recon.actual_amount or 0)}. "
            f"Variance of {inr_diff} indicates potential discount leakage or undercharging."
        )

        evidence = {
            "order_id": recon.entity_id,
            "payment_id": recon.related_entity_id,
            "expected_amount_paise": recon.expected_amount,
            "actual_amount_paise": recon.actual_amount,
            "difference_paise": recon.difference,
            "difference_inr": inr_diff,
            "match_confidence": float(recon.confidence or 0),
        }

        exceptions.append(
            FinancialException(
                case_id=f"CASE-AMM-{recon.id}",
                exception_type="PAYMENT_AMOUNT_MISMATCH",
                risk_level=risk_level,
                value_at_risk=diff,
                status="OPEN",
                suggested_owner="Finance",
                related_order_id=recon.entity_id,
                related_payment_id=recon.related_entity_id,
                evidence=evidence,
                explanation=explanation,
                triggering_rule="PAYMENT_AMOUNT_MISMATCH_RULE: Order total differs from payment gateway captured amount.",
                detected_at=datetime.utcnow(),
            )
        )

    # 2. Settlement Calculation Discrepancies from Phase 2A
    calc_discrepancies = (
        db.query(SettlementCalculation)
        .filter(SettlementCalculation.calculation_status == "DISCREPANCY")
        .all()
    )
    for calc in calc_discrepancies:
        diff = abs(calc.calculation_difference)
        risk_level, score = calculate_exception_priority(diff, 72.0, "CALCULATION_DISCREPANCY")
        inr_diff = _paise_to_inr_str(diff)

        explanation = (
            f"Settlement {calc.settlement_id} reported payout of {_paise_to_inr_str(calc.reported_net_amount)}, "
            f"but deterministic calculation (Gross - Fee - GST - Refunds) yielded {_paise_to_inr_str(calc.expected_net_amount)}. "
            f"Discrepancy of {inr_diff} requires gateway settlement sheet audit."
        )

        evidence = {
            "settlement_id": calc.settlement_id,
            "gross_amount_paise": calc.gross_amount,
            "fee_amount_paise": calc.fee_amount,
            "tax_amount_paise": calc.tax_amount,
            "refund_adjustment_paise": calc.refund_adjustment,
            "other_adjustment_paise": calc.other_adjustment,
            "expected_net_paise": calc.expected_net_amount,
            "reported_net_paise": calc.reported_net_amount,
            "difference_paise": calc.calculation_difference,
            "difference_inr": inr_diff,
        }

        exceptions.append(
            FinancialException(
                case_id=f"CASE-CALC-{calc.settlement_id.replace('SETL-', '')}",
                exception_type="CALCULATION_DISCREPANCY",
                risk_level=risk_level,
                value_at_risk=diff,
                status="OPEN",
                suggested_owner="Finance",
                related_settlement_id=calc.settlement_id,
                evidence=evidence,
                explanation=explanation,
                triggering_rule="SETTLEMENT_CALCULATION_RULE: Reported net payout does not reconcile with verified gross, fee, and tax schedule.",
                detected_at=datetime.utcnow(),
            )
        )

    # 3. Refund Missing in Ledger from Phase 2A
    refund_anomalies = (
        db.query(RefundReconciliationResult)
        .filter(RefundReconciliationResult.refund_status == "REFUND_MISSING_IN_LEDGER")
        .all()
    )
    for ref in refund_anomalies:
        risk_level, score = calculate_exception_priority(ref.refund_amount, 96.0, "REFUND_MISSING_IN_LEDGER")
        inr_ref = _paise_to_inr_str(ref.refund_amount)

        explanation = (
            f"Refund {ref.refund_id} for {inr_ref} was processed by gateway for payment {ref.payment_id or 'N/A'}, "
            f"but has not been booked to accounting general ledger. Books are understated for customer returns."
        )

        evidence = {
            "refund_id": ref.refund_id,
            "payment_id": ref.payment_id,
            "order_id": ref.order_id,
            "settlement_id": ref.settlement_id,
            "refund_amount_paise": ref.refund_amount,
            "refund_amount_inr": inr_ref,
            "refund_status": ref.refund_status,
        }

        exceptions.append(
            FinancialException(
                case_id=f"CASE-REF-{ref.refund_id.replace('rfnd_', '')}",
                exception_type="REFUND_MISSING_IN_LEDGER",
                risk_level=risk_level,
                value_at_risk=ref.refund_amount,
                status="OPEN",
                suggested_owner="Finance",
                related_order_id=ref.order_id,
                related_payment_id=ref.payment_id,
                related_settlement_id=ref.settlement_id,
                evidence=evidence,
                explanation=explanation,
                triggering_rule="REFUND_LEDGER_AUDIT_RULE: Gateway refund record has no corresponding entry in general ledger books.",
                detected_at=datetime.utcnow(),
            )
        )

    return exceptions


def run_all_exception_detection(
    db: Session,
    unfulfilled_threshold_hours: float = 72.0,
    settlement_window_hours: float = 48.0,
    as_of: Optional[datetime] = None,
) -> dict:
    """
    Executes all exception detectors, persists cases to database idempotently,
    and returns detection summary counters.
    """
    # Clear previously generated exceptions
    db.query(FinancialException).delete(synchronize_session=False)
    db.commit()

    unfulfilled = detect_paid_but_unfulfilled(db, unfulfilled_threshold_hours, as_of)
    settlement_missing = detect_settlement_missing_in_bank(db, settlement_window_hours, as_of)
    other_exceptions = ingest_reconciliation_exceptions(db)

    all_cases = unfulfilled + settlement_missing + other_exceptions
    
    # Ensure unique case_ids
    seen_ids = set()
    deduped_cases = []
    for c in all_cases:
        if c.case_id in seen_ids:
            c.case_id = f"{c.case_id}-{len(seen_ids)}"
        seen_ids.add(c.case_id)
        deduped_cases.append(c)

    db.bulk_save_objects(deduped_cases)
    db.commit()

    by_type = {}
    by_risk = {}
    total_var = 0

    for c in deduped_cases:
        by_type[c.exception_type] = by_type.get(c.exception_type, 0) + 1
        by_risk[c.risk_level] = by_risk.get(c.risk_level, 0) + 1
        total_var += c.value_at_risk

    return {
        "total_exceptions": len(deduped_cases),
        "total_value_at_risk_paise": total_var,
        "total_value_at_risk_inr": _paise_to_inr_str(total_var),
        "by_type": by_type,
        "by_risk": by_risk,
        "unfulfilled_detected": len(unfulfilled),
        "settlement_missing_detected": len(settlement_missing),
        "other_anomalies_detected": len(other_exceptions),
    }
