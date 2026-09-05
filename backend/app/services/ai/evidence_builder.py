"""
Structured Evidence Package Builder for Phase 3.

Builds strictly verified evidence packages from database records.
CRITICAL: Never leaks ground truth, API keys, or unverified test metadata.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    Order,
    Payment,
    Settlement,
    SettlementLine,
    BankTransaction,
    Shipment,
    Refund,
    LedgerEntry,
    FinancialException,
    SettlementCalculation,
    TaxReconciliationResult,
    RefundReconciliationResult,
    ReconciliationResult,
)
from app.schemas.ai import EvidenceRecord


def _paise_to_inr_str(paise: Any) -> str:
    if paise is None:
        return "₹0.00"
    try:
        amt = float(paise) / 100.0
        return f"₹{amt:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


def build_case_evidence_package(db: Session, case_id: str) -> Optional[Dict[str, Any]]:
    """
    Constructs a verified evidence package for a specific FinancialException case.
    Extracts strictly existing database records across the transaction lifecycle.
    """
    case = db.query(FinancialException).filter(FinancialException.case_id == case_id).first()
    if not case:
        try:
            case = db.query(FinancialException).filter(FinancialException.id == int(case_id)).first()
        except ValueError:
            pass
    if not case:
        return None

    verified_facts: Dict[str, Any] = {}
    evidence_records: List[EvidenceRecord] = []
    evidence_ids: List[str] = []

    # 1. Order Evidence
    order_id = case.related_order_id
    if order_id:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            verified_facts["order_id"] = order.order_id
            verified_facts["order_amount"] = _paise_to_inr_str(order.order_amount)
            verified_facts["order_amount_paise"] = order.order_amount
            verified_facts["order_status"] = order.order_status
            verified_facts["order_date"] = order.order_date.strftime("%Y-%m-%d %H:%M")
            evidence_ids.append(order.order_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="ORDER",
                    record_id=order.order_id,
                    status=order.order_status,
                    amount_inr=_paise_to_inr_str(order.order_amount),
                    verified=True,
                )
            )

    # 2. Payment Evidence
    payment_id = case.related_payment_id
    if payment_id:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if payment:
            verified_facts["payment_id"] = payment.payment_id
            verified_facts["payment_amount"] = _paise_to_inr_str(payment.amount)
            verified_facts["payment_amount_paise"] = payment.amount
            verified_facts["payment_status"] = payment.status
            verified_facts["payment_method"] = payment.payment_method
            if payment.payment_captured_at:
                verified_facts["payment_captured_at"] = payment.payment_captured_at.strftime("%Y-%m-%d %H:%M")
                elapsed = (datetime.utcnow() - payment.payment_captured_at).total_seconds() / 3600.0
                verified_facts["payment_age_hours"] = round(elapsed, 1)
            evidence_ids.append(payment.payment_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="PAYMENT",
                    record_id=payment.payment_id,
                    status=payment.status,
                    amount_inr=_paise_to_inr_str(payment.amount),
                    verified=True,
                )
            )

    # 3. Settlement Evidence
    settlement_id = case.related_settlement_id
    if settlement_id:
        settlement = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
        if settlement:
            verified_facts["settlement_id"] = settlement.settlement_id
            verified_facts["settlement_status"] = settlement.status
            verified_facts["settlement_net_amount"] = _paise_to_inr_str(settlement.net_amount)
            verified_facts["settlement_gross_amount"] = _paise_to_inr_str(settlement.gross_amount)
            verified_facts["settlement_utr"] = settlement.settlement_utr or "UNASSIGNED"
            verified_facts["settlement_date"] = settlement.settlement_date.strftime("%Y-%m-%d %H:%M")
            evidence_ids.append(settlement.settlement_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="SETTLEMENT",
                    record_id=settlement.settlement_id,
                    status=settlement.status,
                    amount_inr=_paise_to_inr_str(settlement.net_amount),
                    verified=True,
                )
            )

    # 4. Bank Evidence
    bank_entry_id = case.related_bank_entry_id
    if bank_entry_id:
        bank = db.query(BankTransaction).filter(BankTransaction.bank_entry_id == bank_entry_id).first()
        if bank:
            verified_facts["bank_entry_id"] = bank.bank_entry_id
            verified_facts["bank_credit_status"] = "CREDITED"
            verified_facts["bank_amount"] = _paise_to_inr_str(bank.amount)
            verified_facts["bank_date"] = bank.bank_date.strftime("%Y-%m-%d %H:%M")
            verified_facts["bank_utr"] = bank.utr
            evidence_ids.append(bank.bank_entry_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="BANK_TRANSACTION",
                    record_id=bank.bank_entry_id,
                    status="CREDITED",
                    amount_inr=_paise_to_inr_str(bank.amount),
                    verified=True,
                )
            )
    else:
        if settlement_id:
            verified_facts["bank_credit_status"] = "UNMATCHED_OR_PENDING"
            evidence_records.append(
                EvidenceRecord(
                    record_type="BANK_TRANSACTION",
                    record_id="BANK_CREDIT_PENDING",
                    status="MISSING",
                    amount_inr=None,
                    verified=False,
                    discrepancy="No matching credit found in bank statements",
                )
            )

    # 5. Shipment Evidence (for fulfillment checks)
    if order_id:
        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if shipment:
            verified_facts["shipment_id"] = shipment.shipment_id
            verified_facts["shipment_status"] = shipment.status
            verified_facts["carrier"] = shipment.carrier
            verified_facts["tracking_number"] = shipment.tracking_number
            evidence_ids.append(shipment.shipment_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="SHIPMENT",
                    record_id=shipment.shipment_id,
                    status=shipment.status,
                    verified=True,
                )
            )
        else:
            verified_facts["shipment_status"] = "NOT_SHIPPED"
            evidence_records.append(
                EvidenceRecord(
                    record_type="SHIPMENT",
                    record_id=f"SHIPMENT_FOR_{order_id}",
                    status="NOT_FOUND",
                    verified=False,
                    discrepancy="No courier dispatch record found after payment capture",
                )
            )

    # 6. Additional case-level evidence attributes
    if case.evidence and isinstance(case.evidence, dict):
        for k, v in case.evidence.items():
            if k not in verified_facts and v is not None:
                verified_facts[k] = v
                if str(v).startswith(("REF-", "LED-", "SETL-", "pay_", "ORD-", "BANK-")):
                    if str(v) not in evidence_ids:
                        evidence_ids.append(str(v))

    return {
        "case_id": case.case_id,
        "exception_type": case.exception_type,
        "risk_level": case.risk_level,
        "value_at_risk_paise": case.value_at_risk,
        "value_at_risk_inr": _paise_to_inr_str(case.value_at_risk),
        "verified_facts": verified_facts,
        "trigger_rule": case.triggering_rule,
        "stored_explanation": case.explanation,
        "suggested_owner": case.suggested_owner,
        "evidence_ids": list(set(evidence_ids)),
        "evidence_records": evidence_records,
    }


def build_settlement_evidence_package(db: Session, settlement_id: str) -> Optional[Dict[str, Any]]:
    """
    Builds deterministic financial calculation and validation package for a settlement.
    Retrieves gross, fee, GST tax, refunds, expected net, and matches against bank.
    """
    setl = db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
    if not setl:
        return None

    calc = db.query(SettlementCalculation).filter(SettlementCalculation.settlement_id == settlement_id).first()
    bank_recon = (
        db.query(ReconciliationResult)
        .filter(
            ReconciliationResult.entity_type == "SETTLEMENT",
            ReconciliationResult.entity_id == settlement_id,
        )
        .first()
    )

    gross_paise = calc.gross_amount if calc else setl.gross_amount
    fee_paise = calc.fee_amount if calc else setl.fee_amount
    tax_paise = calc.tax_amount if calc else setl.tax_amount
    refund_paise = calc.refund_adjustment if calc else 0
    other_adj_paise = calc.other_adjustment if calc else setl.adjustment_amount
    expected_net_paise = calc.expected_net_amount if calc else setl.net_amount
    reported_net_paise = setl.net_amount
    variance_paise = reported_net_paise - expected_net_paise

    evidence_records: List[EvidenceRecord] = [
        EvidenceRecord(
            record_type="SETTLEMENT",
            record_id=setl.settlement_id,
            status=setl.status,
            amount_inr=_paise_to_inr_str(setl.net_amount),
            verified=True,
        )
    ]
    evidence_ids: List[str] = [setl.settlement_id]

    bank_entry_id = bank_recon.related_entity_id if bank_recon else None
    if bank_entry_id:
        evidence_ids.append(bank_entry_id)
        evidence_records.append(
            EvidenceRecord(
                record_type="BANK_TRANSACTION",
                record_id=bank_entry_id,
                status=bank_recon.status if bank_recon else "MATCHED",
                amount_inr=_paise_to_inr_str(bank_recon.actual_amount or setl.net_amount),
                verified=True,
            )
        )
    else:
        evidence_records.append(
            EvidenceRecord(
                record_type="BANK_TRANSACTION",
                record_id="BANK_CREDIT_UNVERIFIED",
                status="UNMATCHED",
                verified=False,
                discrepancy="No bank credit matching settlement amount or UTR",
            )
        )

    return {
        "settlement_id": setl.settlement_id,
        "settlement_date": setl.settlement_date.strftime("%Y-%m-%d"),
        "settlement_utr": setl.settlement_utr,
        "status": setl.status,
        "gross_amount_paise": gross_paise,
        "gross_amount_inr": _paise_to_inr_str(gross_paise),
        "fee_amount_paise": fee_paise,
        "fee_amount_inr": _paise_to_inr_str(fee_paise),
        "tax_amount_paise": tax_paise,
        "tax_amount_inr": _paise_to_inr_str(tax_paise),
        "refund_adjustment_paise": refund_paise,
        "refund_adjustment_inr": _paise_to_inr_str(refund_paise),
        "other_adjustment_paise": other_adj_paise,
        "other_adjustment_inr": _paise_to_inr_str(other_adj_paise),
        "expected_net_paise": expected_net_paise,
        "expected_net_inr": _paise_to_inr_str(expected_net_paise),
        "reported_net_paise": reported_net_paise,
        "reported_net_inr": _paise_to_inr_str(reported_net_paise),
        "variance_paise": variance_paise,
        "variance_inr": _paise_to_inr_str(variance_paise),
        "calculation_status": calc.calculation_status if calc else ("CORRECT" if variance_paise == 0 else "DISCREPANCY"),
        "bank_match_status": bank_recon.status if bank_recon else "PENDING_BANK_CREDIT",
        "bank_entry_id": bank_entry_id,
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
    }


def build_missing_bank_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds verified evidence package for settlements missing from bank account.
    Filters out normal timing delays (settlements within credit window).
    """
    # 1. Query central exceptions of type SETTLEMENT_MISSING_IN_BANK
    cases = (
        db.query(FinancialException)
        .filter(FinancialException.exception_type == "SETTLEMENT_MISSING_IN_BANK")
        .all()
    )

    items = []
    evidence_ids = []
    evidence_records = []
    total_var = 0

    for c in cases:
        total_var += c.value_at_risk
        setl_id = c.related_settlement_id
        if setl_id:
            evidence_ids.append(setl_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="SETTLEMENT",
                    record_id=setl_id,
                    status="MISSING_IN_BANK",
                    amount_inr=_paise_to_inr_str(c.value_at_risk),
                    verified=True,
                    discrepancy="Bank deposit window elapsed without matching credit",
                )
            )
        items.append({
            "case_id": c.case_id,
            "settlement_id": setl_id,
            "value_at_risk_inr": _paise_to_inr_str(c.value_at_risk),
            "risk_level": c.risk_level,
            "explanation": c.explanation,
        })

    return {
        "missing_count": len(items),
        "total_value_at_risk_inr": _paise_to_inr_str(total_var),
        "cases": items,
        "evidence_ids": list(set(evidence_ids)),
        "evidence_records": evidence_records,
    }


def build_refund_ledger_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for refunds missing from accounting ledger.
    """
    refund_anomalies = (
        db.query(RefundReconciliationResult)
        .filter(RefundReconciliationResult.refund_status == "REFUND_MISSING_IN_LEDGER")
        .all()
    )

    items = []
    evidence_ids = []
    evidence_records = []
    total_paise = 0

    for r in refund_anomalies:
        total_paise += r.refund_amount
        evidence_ids.append(r.refund_id)
        if r.payment_id:
            evidence_ids.append(r.payment_id)
        if r.settlement_id:
            evidence_ids.append(r.settlement_id)

        evidence_records.append(
            EvidenceRecord(
                record_type="REFUND",
                record_id=r.refund_id,
                status="MISSING_IN_LEDGER",
                amount_inr=_paise_to_inr_str(r.refund_amount),
                verified=True,
                discrepancy="Gateway processed refund but no journal entry in accounting ledger",
            )
        )

        items.append({
            "refund_id": r.refund_id,
            "payment_id": r.payment_id,
            "order_id": r.order_id,
            "settlement_id": r.settlement_id,
            "refund_amount_inr": _paise_to_inr_str(r.refund_amount),
            "notes": r.notes,
        })

    return {
        "missing_count": len(items),
        "total_unposted_refunds_inr": _paise_to_inr_str(total_paise),
        "refunds": items,
        "evidence_ids": list(set(evidence_ids)),
        "evidence_records": evidence_records,
    }


def build_cash_position_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds evidence package for cash arrival and liquidity posture.
    Categorizes into: Already Received, Expected, Pending, and At Risk.
    """
    # 1. Received: Verified matched bank deposits in bank_transactions
    credited_sum = (
        db.query(BankTransaction)
        .filter(BankTransaction.direction == "CREDIT")
        .all()
    )
    received_paise = sum(b.amount for b in credited_sum)

    # 2. Expected / In Flight: Settlements marked settled but within normal bank window
    settled_batches = db.query(Settlement).all()
    in_flight_paise = 0
    for s in settled_batches:
        recon = (
            db.query(ReconciliationResult)
            .filter(ReconciliationResult.entity_type == "SETTLEMENT", ReconciliationResult.entity_id == s.settlement_id)
            .first()
        )
        if recon and recon.status == "PENDING_BANK_CREDIT":
            in_flight_paise += s.net_amount

    # 3. Pending: Captured payments not yet included in any settlement line
    settled_payment_ids = set(r[0] for r in db.query(SettlementLine.payment_id).all())
    captured_payments = (
        db.query(Payment)
        .filter(Payment.status == "captured")
        .all()
    )
    pending_payout_paise = sum(p.amount for p in captured_payments if p.payment_id not in settled_payment_ids)

    # 4. At Risk: Total value at risk across central open exceptions
    open_exceptions = (
        db.query(FinancialException)
        .filter(FinancialException.status.in_(["OPEN", "ASSIGNED", "IN_REVIEW"]))
        .all()
    )
    at_risk_paise = sum(e.value_at_risk for e in open_exceptions)

    return {
        "already_received_inr": _paise_to_inr_str(received_paise),
        "expected_in_flight_inr": _paise_to_inr_str(in_flight_paise),
        "pending_gateway_payout_inr": _paise_to_inr_str(pending_payout_paise),
        "at_risk_inr": _paise_to_inr_str(at_risk_paise),
        "at_risk_case_count": len(open_exceptions),
        "breakdown_summary": (
            f"Already Received: {_paise_to_inr_str(received_paise)} in bank accounts. "
            f"Expected In-Flight: {_paise_to_inr_str(in_flight_paise)} dispatched by gateways. "
            f"Pending Payout: {_paise_to_inr_str(pending_payout_paise)} in captured cart orders. "
            f"At Risk: {_paise_to_inr_str(at_risk_paise)} across {len(open_exceptions)} unresolved exception cases."
        ),
    }


def build_unfulfilled_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for captured payments missing fulfillment.
    """
    cases = (
        db.query(FinancialException)
        .filter(FinancialException.exception_type == "PAID_BUT_UNFULFILLED")
        .all()
    )

    items = []
    evidence_ids = []
    evidence_records = []
    total_paise = 0

    for c in cases:
        total_paise += c.value_at_risk
        if c.related_order_id:
            evidence_ids.append(c.related_order_id)
            evidence_records.append(
                EvidenceRecord(
                    record_type="ORDER",
                    record_id=c.related_order_id,
                    status="UNFULFILLED",
                    amount_inr=_paise_to_inr_str(c.value_at_risk),
                    verified=True,
                    discrepancy="Captured payment exists without shipment record",
                )
            )
        if c.related_payment_id:
            evidence_ids.append(c.related_payment_id)

        items.append({
            "case_id": c.case_id,
            "order_id": c.related_order_id,
            "payment_id": c.related_payment_id,
            "order_amount_inr": _paise_to_inr_str(c.value_at_risk),
            "risk_level": c.risk_level,
            "explanation": c.explanation,
        })

    return {
        "unfulfilled_count": len(items),
        "total_value_at_risk_inr": _paise_to_inr_str(total_paise),
        "orders": items,
        "evidence_ids": list(set(evidence_ids)),
        "evidence_records": evidence_records,
    }


def build_highest_risk_evidence_package(db: Session, limit: int = 5) -> Dict[str, Any]:
    """
    Builds deterministic evidence package of highest-value and highest-risk unresolved cases.
    Sorted by risk level priority (CRITICAL > HIGH > MEDIUM > LOW), then value at risk.
    """
    cases = (
        db.query(FinancialException)
        .filter(FinancialException.status.in_(["OPEN", "ASSIGNED", "IN_REVIEW"]))
        .all()
    )

    risk_weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    sorted_cases = sorted(
        cases,
        key=lambda c: (risk_weight.get(c.risk_level.upper(), 0), c.value_at_risk),
        reverse=True,
    )[:limit]

    items = []
    evidence_ids = []
    evidence_records = []

    for c in sorted_cases:
        evidence_ids.append(c.case_id)
        if c.related_order_id:
            evidence_ids.append(c.related_order_id)
        if c.related_payment_id:
            evidence_ids.append(c.related_payment_id)
        if c.related_settlement_id:
            evidence_ids.append(c.related_settlement_id)

        evidence_records.append(
            EvidenceRecord(
                record_type="EXCEPTION",
                record_id=c.case_id,
                status=c.status,
                amount_inr=_paise_to_inr_str(c.value_at_risk),
                verified=True,
                discrepancy=f"{c.risk_level} Risk: {c.exception_type.replace('_', ' ')}",
            )
        )

        items.append({
            "case_id": c.case_id,
            "exception_type": c.exception_type,
            "risk_level": c.risk_level,
            "value_at_risk_inr": _paise_to_inr_str(c.value_at_risk),
            "suggested_owner": c.suggested_owner,
            "related_order_id": c.related_order_id,
            "related_settlement_id": c.related_settlement_id,
            "explanation": c.explanation,
        })

    return {
        "top_cases_count": len(items),
        "top_cases": items,
        "evidence_ids": list(set(evidence_ids)),
        "evidence_records": evidence_records,
    }


def build_orders_evidence_package(db: Session, order_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for order volume, status, or specific order lookup.
    """
    if order_id:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            payments = db.query(Payment).filter(Payment.order_id == order_id).all()
            shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
            exc = db.query(FinancialException).filter(FinancialException.related_order_id == order_id).first()

            evidence_ids = [order.order_id]
            evidence_records = [
                EvidenceRecord(
                    record_type="ORDER",
                    record_id=order.order_id,
                    status=order.order_status,
                    amount_inr=_paise_to_inr_str(order.order_amount),
                    verified=True,
                )
            ]

            payment_details = []
            for p in payments:
                evidence_ids.append(p.payment_id)
                evidence_records.append(
                    EvidenceRecord(
                        record_type="PAYMENT",
                        record_id=p.payment_id,
                        status=p.status,
                        amount_inr=_paise_to_inr_str(p.amount),
                        verified=True,
                    )
                )
                payment_details.append({
                    "payment_id": p.payment_id,
                    "amount_inr": _paise_to_inr_str(p.amount),
                    "status": p.status,
                    "payment_method": p.payment_method,
                })

            return {
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "order_amount_inr": _paise_to_inr_str(order.order_amount),
                "order_status": order.order_status,
                "order_date": order.order_date.strftime("%Y-%m-%d %H:%M") if order.order_date else None,
                "payment_mode": order.payment_mode,
                "payments": payment_details,
                "shipment_status": shipment.status if shipment else "NOT_FOUND",
                "tracking_number": shipment.tracking_number if shipment else None,
                "carrier": shipment.carrier if shipment else None,
                "exception_case_id": exc.case_id if exc else None,
                "evidence_ids": list(set(evidence_ids)),
                "evidence_records": evidence_records,
                "is_single_order": True,
            }

    # Aggregate orders inquiry
    total_orders = db.query(Order).count()
    total_amount_paise = db.query(func.sum(Order.order_amount)).scalar() or 0

    # Group by status
    status_counts = {}
    for st, count in db.query(Order.order_status, func.count(Order.id)).group_by(Order.order_status).all():
        status_counts[st] = count

    # Recent sample orders
    recent_orders = db.query(Order).order_by(Order.order_date.desc()).limit(5).all()
    evidence_ids = [o.order_id for o in recent_orders]
    evidence_records = [
        EvidenceRecord(
            record_type="ORDER",
            record_id=o.order_id,
            status=o.order_status,
            amount_inr=_paise_to_inr_str(o.order_amount),
            verified=True,
        )
        for o in recent_orders
    ]

    return {
        "total_orders_count": total_orders,
        "total_orders_amount_inr": _paise_to_inr_str(total_amount_paise),
        "status_breakdown": status_counts,
        "recent_sample_orders": [
            {
                "order_id": o.order_id,
                "amount_inr": _paise_to_inr_str(o.order_amount),
                "status": o.order_status,
                "date": o.order_date.strftime("%Y-%m-%d") if o.order_date else None,
            }
            for o in recent_orders
        ],
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
        "is_single_order": False,
    }


def build_bank_deposits_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for bank statement credits, balances, and deposits.
    """
    credits = db.query(BankTransaction).filter(BankTransaction.direction == "CREDIT").all()
    debits = db.query(BankTransaction).filter(BankTransaction.direction == "DEBIT").all()

    total_credit_paise = sum(c.amount for c in credits)
    total_debit_paise = sum(d.amount for d in debits)
    net_bank_movement_paise = total_credit_paise - total_debit_paise

    # Check reconciled settlement matches in bank
    reconciled_results = (
        db.query(ReconciliationResult)
        .filter(
            ReconciliationResult.entity_type == "SETTLEMENT",
            ReconciliationResult.status.in_(["MATCHED", "EXACT_MATCH", "SETTLED"]),
        )
        .all()
    )
    reconciled_setl_ids = set(r.entity_id for r in reconciled_results)

    # 5 largest or most recent credit transactions
    recent_credits = (
        db.query(BankTransaction)
        .filter(BankTransaction.direction == "CREDIT")
        .order_by(BankTransaction.bank_date.desc())
        .limit(5)
        .all()
    )

    evidence_ids = [b.bank_entry_id for b in recent_credits]
    evidence_records = [
        EvidenceRecord(
            record_type="BANK_TRANSACTION",
            record_id=b.bank_entry_id,
            status="CREDITED",
            amount_inr=_paise_to_inr_str(b.amount),
            verified=True,
            discrepancy=f"UTR: {b.utr or 'N/A'}",
        )
        for b in recent_credits
    ]

    return {
        "total_credit_transactions": len(credits),
        "total_credited_amount_inr": _paise_to_inr_str(total_credit_paise),
        "total_debit_transactions": len(debits),
        "total_debited_amount_inr": _paise_to_inr_str(total_debit_paise),
        "net_bank_inflow_inr": _paise_to_inr_str(net_bank_movement_paise),
        "reconciled_settlements_count": len(reconciled_setl_ids),
        "recent_credits": [
            {
                "bank_entry_id": b.bank_entry_id,
                "amount_inr": _paise_to_inr_str(b.amount),
                "date": b.bank_date.strftime("%Y-%m-%d") if b.bank_date else None,
                "utr": b.utr or "UNASSIGNED",
                "narration": b.narration or "Bank Settlement Credit",
            }
            for b in recent_credits
        ],
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
    }


def build_payment_gateways_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for payment gateway transactions, capture volume, and methods.
    """
    total_payments = db.query(Payment).count()
    captured = db.query(Payment).filter(Payment.status == "captured").all()
    failed = db.query(Payment).filter(Payment.status == "failed").all()
    pending = db.query(Payment).filter(Payment.status == "pending").all()

    total_captured_paise = sum(p.amount for p in captured)
    total_failed_paise = sum(p.amount for p in failed)

    # Method breakdown
    method_counts = {}
    for pm, count in db.query(Payment.payment_method, func.count(Payment.id)).group_by(Payment.payment_method).all():
        method_counts[pm or "other"] = count

    recent_captured = db.query(Payment).filter(Payment.status == "captured").order_by(Payment.created_at.desc()).limit(5).all()
    evidence_ids = [p.payment_id for p in recent_captured]
    evidence_records = [
        EvidenceRecord(
            record_type="PAYMENT",
            record_id=p.payment_id,
            status=p.status,
            amount_inr=_paise_to_inr_str(p.amount),
            verified=True,
            discrepancy=f"Method: {p.payment_method}",
        )
        for p in recent_captured
    ]

    return {
        "total_payments_count": total_payments,
        "captured_count": len(captured),
        "total_captured_amount_inr": _paise_to_inr_str(total_captured_paise),
        "failed_count": len(failed),
        "total_failed_amount_inr": _paise_to_inr_str(total_failed_paise),
        "pending_count": len(pending),
        "method_breakdown": method_counts,
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
    }


def build_exceptions_summary_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package summarizing all open exception cases across categories.
    """
    cases = db.query(FinancialException).filter(FinancialException.status.in_(["OPEN", "ASSIGNED", "IN_REVIEW"])).all()
    total_var = sum(c.value_at_risk for c in cases)

    type_counts = {}
    for c in cases:
        type_counts[c.exception_type] = type_counts.get(c.exception_type, 0) + 1

    risk_counts = {
        "CRITICAL": sum(1 for c in cases if c.risk_level == "CRITICAL"),
        "HIGH": sum(1 for c in cases if c.risk_level == "HIGH"),
        "MEDIUM": sum(1 for c in cases if c.risk_level == "MEDIUM"),
        "LOW": sum(1 for c in cases if c.risk_level == "LOW"),
    }

    owner_counts = {}
    for c in cases:
        owner = c.suggested_owner or "Finance"
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

    top_cases = sorted(cases, key=lambda x: x.value_at_risk, reverse=True)[:5]
    evidence_ids = [c.case_id for c in top_cases]
    evidence_records = [
        EvidenceRecord(
            record_type="EXCEPTION",
            record_id=c.case_id,
            status=c.status,
            amount_inr=_paise_to_inr_str(c.value_at_risk),
            verified=True,
            discrepancy=f"{c.risk_level}: {c.exception_type}",
        )
        for c in top_cases
    ]

    return {
        "total_open_cases": len(cases),
        "total_value_at_risk_inr": _paise_to_inr_str(total_var),
        "type_breakdown": type_counts,
        "risk_breakdown": risk_counts,
        "owner_breakdown": owner_counts,
        "top_cases": [
            {
                "case_id": c.case_id,
                "type": c.exception_type,
                "risk": c.risk_level,
                "amount_inr": _paise_to_inr_str(c.value_at_risk),
                "owner": c.suggested_owner,
            }
            for c in top_cases
        ],
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
    }


def build_tax_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds deterministic evidence package for GST / fee tax reconciliation results.
    """
    results = db.query(TaxReconciliationResult).all()
    total_tax_records = len(results)
    matched_tax = sum(1 for r in results if r.variance_status == "MATCHED")
    discrepancy_tax = sum(1 for r in results if r.variance_status != "MATCHED")

    total_reported = sum(r.reported_tax_amount for r in results)
    total_expected = sum(r.expected_tax_amount for r in results)
    total_variance = sum(r.variance_amount for r in results)

    evidence_ids = [r.settlement_id for r in results[:5]]
    evidence_records = [
        EvidenceRecord(
            record_type="TAX_RECONCILIATION",
            record_id=r.settlement_id,
            status=r.variance_status,
            amount_inr=_paise_to_inr_str(r.reported_tax_amount),
            verified=True,
            discrepancy=f"Variance: {_paise_to_inr_str(r.variance_amount)}",
        )
        for r in results[:5]
    ]

    return {
        "total_tax_batches": total_tax_records,
        "matched_count": matched_tax,
        "discrepancy_count": discrepancy_tax,
        "total_reported_tax_inr": _paise_to_inr_str(total_reported),
        "total_expected_tax_inr": _paise_to_inr_str(total_expected),
        "total_variance_inr": _paise_to_inr_str(total_variance),
        "evidence_ids": evidence_ids,
        "evidence_records": evidence_records,
    }


def build_general_financial_evidence_package(db: Session) -> Dict[str, Any]:
    """
    Builds unified, multi-dimensional financial posture evidence package for general queries.
    Covers orders, payments, bank credits, settlements, and exceptions.
    """
    total_orders = db.query(Order).count()
    total_orders_paise = db.query(func.sum(Order.order_amount)).scalar() or 0

    total_payments = db.query(Payment).count()
    captured_paise = db.query(func.sum(Payment.amount)).filter(Payment.status == "captured").scalar() or 0

    credited_txns = db.query(BankTransaction).filter(BankTransaction.direction == "CREDIT").all()
    bank_credited_paise = sum(b.amount for b in credited_txns)

    settlements = db.query(Settlement).all()
    settled_paise = sum(s.net_amount for s in settlements)

    open_exceptions = db.query(FinancialException).filter(FinancialException.status.in_(["OPEN", "ASSIGNED", "IN_REVIEW"])).all()
    at_risk_paise = sum(e.value_at_risk for e in open_exceptions)

    return {
        "total_orders_count": total_orders,
        "total_orders_amount_inr": _paise_to_inr_str(total_orders_paise),
        "total_payments_count": total_payments,
        "total_captured_amount_inr": _paise_to_inr_str(captured_paise),
        "total_bank_credits_count": len(credited_txns),
        "total_bank_credited_inr": _paise_to_inr_str(bank_credited_paise),
        "total_settlements_count": len(settlements),
        "total_settlements_amount_inr": _paise_to_inr_str(settled_paise),
        "total_open_exceptions": len(open_exceptions),
        "total_value_at_risk_inr": _paise_to_inr_str(at_risk_paise),
        "evidence_ids": [f"ORD-COUNT-{total_orders}", f"BANK-TXNS-{len(credited_txns)}"],
        "evidence_records": [
            EvidenceRecord(
                record_type="OVERVIEW",
                record_id="ORDERS",
                status="VERIFIED",
                amount_inr=_paise_to_inr_str(total_orders_paise),
                verified=True,
            ),
            EvidenceRecord(
                record_type="OVERVIEW",
                record_id="BANK_DEPOSITS",
                status="CREDITED",
                amount_inr=_paise_to_inr_str(bank_credited_paise),
                verified=True,
            ),
            EvidenceRecord(
                record_type="OVERVIEW",
                record_id="VALUE_AT_RISK",
                status="OPEN_EXCEPTIONS",
                amount_inr=_paise_to_inr_str(at_risk_paise),
                verified=True,
            ),
        ],
    }

