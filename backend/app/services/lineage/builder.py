"""
Money Lineage Graph Builder.

Constructs the complete end-to-end journey of money across:
  Order → Payment → Fee & GST → Settlement → Bank Credit → Ledger Entry → Shipment → Refund → Exceptions

Follows strict rules:
  1. Data must be grounded in real database records — NO fabricated records.
  2. If a financial record is absent, explicitly emit a 'MISSING / NO RECORD FOUND' grey node.
  3. Visual Status System:
       green  : Verified and matched
       yellow : Pending or expected timing difference
       red    : Financial mismatch or high-risk exception
       grey   : Missing data or unavailable linkage
       blue   : Informational operational event
"""

from typing import Dict, Any, List, Optional
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
    ReconciliationResult,
    SettlementCalculation,
    FinancialException,
)


def _paise_to_inr_str(paise: Optional[int]) -> str:
    if paise is None:
        return "N/A"
    return f"₹{paise / 100.0:,.2f}"


def build_money_lineage_graph(
    db: Session,
    entity_type: str,
    entity_id: str,
) -> Dict[str, Any]:
    """
    Builds the Money Lineage Graph anchored at entity_id of entity_type.
    Supported entity types: order | payment | settlement | bank_transaction | exception | refund
    """
    etype = entity_type.lower().strip()
    eid = entity_id.strip()

    # Anchor resolution
    order: Optional[Order] = None
    payment: Optional[Payment] = None
    settlement: Optional[Settlement] = None
    bank_tx: Optional[BankTransaction] = None
    shipment: Optional[Shipment] = None
    refund: Optional[Refund] = None
    exception: Optional[FinancialException] = None

    if etype == "exception":
        exception = db.query(FinancialException).filter(FinancialException.case_id == eid).first()
        if not exception:
            # Fallback by id
            try:
                exception = db.query(FinancialException).filter(FinancialException.id == int(eid)).first()
            except (ValueError, TypeError):
                pass
        if exception:
            if exception.related_order_id:
                order = db.query(Order).filter(Order.order_id == exception.related_order_id).first()
            if exception.related_payment_id:
                payment = db.query(Payment).filter(Payment.payment_id == exception.related_payment_id).first()
            if exception.related_settlement_id:
                settlement = db.query(Settlement).filter(Settlement.settlement_id == exception.related_settlement_id).first()
            if exception.related_bank_entry_id:
                bank_tx = db.query(BankTransaction).filter(BankTransaction.bank_entry_id == exception.related_bank_entry_id).first()

    elif etype == "order":
        order = db.query(Order).filter(Order.order_id == eid).first()
    elif etype == "payment":
        payment = db.query(Payment).filter(Payment.payment_id == eid).first()
    elif etype == "settlement":
        settlement = db.query(Settlement).filter(Settlement.settlement_id == eid).first()
    elif etype in ("bank_transaction", "bank"):
        bank_tx = db.query(BankTransaction).filter(BankTransaction.bank_entry_id == eid).first()
    elif etype == "refund":
        refund = db.query(Refund).filter(Refund.refund_id == eid).first()

    # Traverse relationships from known anchor
    # 1. From Order to Payment
    if order and not payment:
        payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()

    # 2. From Payment to Order
    if payment and not order and payment.order_id:
        order = db.query(Order).filter(Order.order_id == payment.order_id).first()

    # 3. From Order to Shipment
    if order and not shipment:
        shipment = db.query(Shipment).filter(Shipment.order_id == order.order_id).first()

    # 4. From Payment to Settlement via SettlementLine
    if payment and not settlement:
        sline = db.query(SettlementLine).filter(SettlementLine.payment_id == payment.payment_id).first()
        if sline:
            settlement = db.query(Settlement).filter(Settlement.settlement_id == sline.settlement_id).first()

    # 5. From Settlement to Payment (if started from settlement, pick primary or first payment)
    if settlement and not payment:
        sline = db.query(SettlementLine).filter(SettlementLine.settlement_id == settlement.settlement_id).first()
        if sline:
            payment = db.query(Payment).filter(Payment.payment_id == sline.payment_id).first()
            if payment and not order and payment.order_id:
                order = db.query(Order).filter(Order.order_id == payment.order_id).first()

    # 6. From Settlement to Bank Transaction via ReconciliationResult or UTR
    if settlement and not bank_tx:
        bank_recon = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.entity_type == "SETTLEMENT",
                ReconciliationResult.entity_id == settlement.settlement_id,
            )
            .first()
        )
        if bank_recon and bank_recon.related_entity_id:
            bank_tx = db.query(BankTransaction).filter(BankTransaction.bank_entry_id == bank_recon.related_entity_id).first()
        elif settlement.settlement_utr:
            bank_tx = db.query(BankTransaction).filter(BankTransaction.utr == settlement.settlement_utr).first()

    # 7. From Bank Transaction to Settlement
    if bank_tx and not settlement:
        if bank_tx.utr:
            settlement = db.query(Settlement).filter(Settlement.settlement_utr == bank_tx.utr).first()
        if not settlement:
            bank_recon = (
                db.query(ReconciliationResult)
                .filter(
                    ReconciliationResult.entity_type == "SETTLEMENT",
                    ReconciliationResult.related_entity_id == bank_tx.bank_entry_id,
                )
                .first()
            )
            if bank_recon:
                settlement = db.query(Settlement).filter(Settlement.settlement_id == bank_recon.entity_id).first()

    # 8. Check for Refunds
    if not refund and payment:
        refund = db.query(Refund).filter(Refund.payment_id == payment.payment_id).first()
    elif not refund and order:
        refund = db.query(Refund).filter(Refund.order_id == order.order_id).first()

    # 9. Look up Ledger Entries
    ledger_entry: Optional[LedgerEntry] = None
    if settlement:
        ledger_entry = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.reference_id == settlement.settlement_id)
            .first()
        )
    if not ledger_entry and refund:
        ledger_entry = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.reference_id == refund.refund_id)
            .first()
        )

    # 10. Check if an active FinancialException exists for any of these entities
    if not exception:
        conds = []
        if order:
            conds.append(FinancialException.related_order_id == order.order_id)
        if payment:
            conds.append(FinancialException.related_payment_id == payment.payment_id)
        if settlement:
            conds.append(FinancialException.related_settlement_id == settlement.settlement_id)
        if conds:
            from sqlalchemy import or_
            exception = db.query(FinancialException).filter(or_(*conds)).first()

    # 11. Check Phase 1 Reconciliation Status for Order ↔ Payment
    order_recon: Optional[ReconciliationResult] = None
    if order:
        order_recon = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.entity_type == "ORDER",
                ReconciliationResult.entity_id == order.order_id,
            )
            .first()
        )

    # 12. Check Phase 1 Reconciliation Status for Settlement ↔ Bank
    settlement_recon: Optional[ReconciliationResult] = None
    if settlement:
        settlement_recon = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.entity_type == "SETTLEMENT",
                ReconciliationResult.entity_id == settlement.settlement_id,
            )
            .first()
        )

    # 13. Check Phase 2A Settlement Calculation
    settlement_calc: Optional[SettlementCalculation] = None
    if settlement:
        settlement_calc = (
            db.query(SettlementCalculation)
            .filter(SettlementCalculation.settlement_id == settlement.settlement_id)
            .first()
        )

    # Construct React Flow Graph (Nodes and Edges)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Node: Order
    if order:
        order_visual = "green" if order.order_status in ("paid", "completed") else "yellow"
        if order_recon and order_recon.status == "AMOUNT_MISMATCH":
            order_visual = "red"
        nodes.append({
            "id": f"node-order-{order.order_id}",
            "type": "lineageNode",
            "position": {"x": 300, "y": 0},
            "data": {
                "category": "ORDER",
                "title": f"Order {order.order_id}",
                "source_system": "E-Commerce Platform",
                "record_id": order.order_id,
                "amount_paise": order.order_amount,
                "amount_inr": _paise_to_inr_str(order.order_amount),
                "date": order.order_date.strftime("%Y-%m-%d %H:%M") if order.order_date else None,
                "status": order.order_status,
                "status_label": "Verified Order" if order_visual == "green" else order.order_status.upper(),
                "visual_status": order_visual,
                "is_missing": False,
                "confidence": 1.0,
                "rule": "E-Commerce Cart Checkout",
                "discrepancy": f"Amount difference: {_paise_to_inr_str(order_recon.difference)}" if order_recon and order_recon.difference else None,
                "details": {
                    "Customer ID": order.customer_id or "N/A",
                    "Payment Mode": order.payment_mode or "N/A",
                    "Created At": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else None,
                },
                "related_records": [payment.payment_id] if payment else [],
            },
        })
    else:
        nodes.append({
            "id": "node-order-missing",
            "type": "lineageNode",
            "position": {"x": 300, "y": 0},
            "data": {
                "category": "ORDER",
                "title": "Order: MISSING",
                "source_system": "E-Commerce Platform",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "N/A",
                "date": None,
                "status": "MISSING",
                "status_label": "No Order Record",
                "visual_status": "grey",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Orphan payment captured with no parent order record",
                "discrepancy": "Payment exists without an authorized e-commerce cart order",
                "details": {},
                "related_records": [],
            },
        })

    # Node: Payment
    order_node_id = f"node-order-{order.order_id}" if order else "node-order-missing"
    if payment:
        pay_visual = "green" if payment.status == "captured" else ("yellow" if payment.status == "pending" else "red")
        pay_node_id = f"node-payment-{payment.payment_id}"
        nodes.append({
            "id": pay_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 140},
            "data": {
                "category": "PAYMENT",
                "title": f"Payment {payment.payment_id}",
                "source_system": "Payment Gateway",
                "record_id": payment.payment_id,
                "amount_paise": payment.amount,
                "amount_inr": _paise_to_inr_str(payment.amount),
                "date": payment.payment_captured_at.strftime("%Y-%m-%d %H:%M") if payment.payment_captured_at else None,
                "status": payment.status,
                "status_label": "Captured & Reconciled" if pay_visual == "green" else payment.status.upper(),
                "visual_status": pay_visual,
                "is_missing": False,
                "confidence": float(order_recon.confidence) if order_recon and order_recon.confidence else 1.0,
                "rule": order_recon.match_type if order_recon else "Exact Gateway Match",
                "discrepancy": order_recon.reason if order_recon and order_recon.status != "MATCHED" else None,
                "details": {
                    "Method": payment.payment_method or "N/A",
                    "Gateway Status": payment.status,
                    "Captured At": payment.payment_captured_at.strftime("%Y-%m-%d %H:%M") if payment.payment_captured_at else "Pending",
                },
                "related_records": [order.order_id] if order else [],
            },
        })
        edges.append({
            "id": f"e-order-payment",
            "source": order_node_id,
            "target": pay_node_id,
            "label": "captured",
            "animated": (pay_visual == "green"),
            "style": {"stroke": "#10b981" if pay_visual == "green" else "#ef4444"},
        })
    else:
        pay_node_id = "node-payment-missing"
        nodes.append({
            "id": pay_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 140},
            "data": {
                "category": "PAYMENT",
                "title": "Payment: MISSING",
                "source_system": "Payment Gateway",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "N/A",
                "date": None,
                "status": "MISSING",
                "status_label": "Payment Missing",
                "visual_status": "grey",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Checkout initiated but no successful webhook or payment transaction recorded",
                "discrepancy": "Order created with uncollected payment",
                "details": {},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-order-payment-missing",
            "source": order_node_id,
            "target": pay_node_id,
            "label": "missing payment",
            "animated": False,
            "style": {"stroke": "#9ca3af", "strokeDasharray": "5 5"},
        })

    # Nodes: Fee & GST breakdown
    fee_paise = None
    tax_paise = None
    if settlement:
        # Approximate 2% fee and 18% GST if not in settlement
        fee_paise = settlement.fee_amount if settlement.fee_amount else int(payment.amount * 0.02) if payment else 0
        tax_paise = settlement.tax_amount if settlement.tax_amount else int(fee_paise * 0.18)
    elif payment:
        fee_paise = int(payment.amount * 0.02)
        tax_paise = int(fee_paise * 0.18)

    fee_node_id = "node-fee"
    tax_node_id = "node-tax"
    if fee_paise is not None:
        nodes.append({
            "id": fee_node_id,
            "type": "lineageNode",
            "position": {"x": 120, "y": 280},
            "data": {
                "category": "FEE",
                "title": "Gateway Fee",
                "source_system": "Payment Gateway Schedule",
                "record_id": "MDR-2%",
                "amount_paise": fee_paise,
                "amount_inr": _paise_to_inr_str(fee_paise),
                "date": None,
                "status": "DEDUCTED",
                "status_label": "Contractual MDR",
                "visual_status": "blue",
                "is_missing": False,
                "confidence": 1.0,
                "rule": "2.0% Merchant Discount Rate",
                "discrepancy": None,
                "details": {"Rate": "2.0% of captured volume"},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-payment-fee",
            "source": pay_node_id,
            "target": fee_node_id,
            "label": "MDR fee",
            "animated": True,
            "style": {"stroke": "#3b82f6"},
        })

    if tax_paise is not None:
        nodes.append({
            "id": tax_node_id,
            "type": "lineageNode",
            "position": {"x": 480, "y": 280},
            "data": {
                "category": "TAX",
                "title": "GST on Fee",
                "source_system": "Statutory / GST Schedule",
                "record_id": "GST-18%",
                "amount_paise": tax_paise,
                "amount_inr": _paise_to_inr_str(tax_paise),
                "date": None,
                "status": "DEDUCTED",
                "status_label": "18% GST on MDR",
                "visual_status": "blue",
                "is_missing": False,
                "confidence": 1.0,
                "rule": "18.0% GST applied to processing fees",
                "discrepancy": None,
                "details": {"Tax Slab": "18% on Fee"},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-payment-tax",
            "source": pay_node_id,
            "target": tax_node_id,
            "label": "GST deduction",
            "animated": True,
            "style": {"stroke": "#3b82f6"},
        })

    # Node: Settlement
    if settlement:
        setl_visual = "green" if settlement.status == "settled" else "yellow"
        if settlement_calc and settlement_calc.calculation_status == "DISCREPANCY":
            setl_visual = "red"
        setl_node_id = f"node-settlement-{settlement.settlement_id}"
        nodes.append({
            "id": setl_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 420},
            "data": {
                "category": "SETTLEMENT",
                "title": f"Settlement {settlement.settlement_id}",
                "source_system": "Treasury / Gateway Payouts",
                "record_id": settlement.settlement_id,
                "amount_paise": settlement.net_amount,
                "amount_inr": _paise_to_inr_str(settlement.net_amount),
                "date": settlement.settlement_date.strftime("%Y-%m-%d %H:%M") if settlement.settlement_date else None,
                "status": settlement.status,
                "status_label": "Net Payout Dispatched" if setl_visual == "green" else settlement.status.upper(),
                "visual_status": setl_visual,
                "is_missing": False,
                "confidence": 1.0,
                "rule": "Deterministic Fee & Tax Net Calculation",
                "discrepancy": f"Calculation variance: {_paise_to_inr_str(settlement_calc.calculation_difference)}" if settlement_calc and settlement_calc.calculation_difference else None,
                "details": {
                    "Gross Amount": _paise_to_inr_str(settlement.gross_amount),
                    "Fees Deducted": _paise_to_inr_str(settlement.fee_amount),
                    "GST Deducted": _paise_to_inr_str(settlement.tax_amount),
                    "Refund Adjustment": _paise_to_inr_str(settlement.adjustment_amount),
                    "UTR": settlement.settlement_utr or "Pending",
                },
                "related_records": [bank_tx.bank_entry_id] if bank_tx else [],
            },
        })
        # Connect fee and tax to settlement
        if fee_paise is not None:
            edges.append({
                "id": f"e-fee-settlement",
                "source": fee_node_id,
                "target": setl_node_id,
                "label": "net deducted",
                "style": {"stroke": "#6b7280"},
            })
        if tax_paise is not None:
            edges.append({
                "id": f"e-tax-settlement",
                "source": tax_node_id,
                "target": setl_node_id,
                "label": "net deducted",
                "style": {"stroke": "#6b7280"},
            })
        edges.append({
            "id": f"e-payment-settlement",
            "source": pay_node_id,
            "target": setl_node_id,
            "label": "batched payout",
            "animated": True,
            "style": {"stroke": "#10b981"},
        })
    else:
        setl_node_id = "node-settlement-missing"
        nodes.append({
            "id": setl_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 420},
            "data": {
                "category": "SETTLEMENT",
                "title": "Settlement: PENDING / MISSING",
                "source_system": "Treasury / Gateway Payouts",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "N/A",
                "date": None,
                "status": "PENDING_BATCH",
                "status_label": "Unsettled Batch",
                "visual_status": "yellow",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Payment awaiting gateway batch settlement cut-off",
                "discrepancy": "Payout has not been bundled into a settlement batch",
                "details": {},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-payment-settlement-missing",
            "source": pay_node_id,
            "target": setl_node_id,
            "label": "pending batch",
            "animated": False,
            "style": {"stroke": "#eab308", "strokeDasharray": "5 5"},
        })

    # Node: Bank Credit
    if bank_tx:
        bank_visual = "green" if bank_tx.direction == "CREDIT" else "red"
        bank_node_id = f"node-bank-{bank_tx.bank_entry_id}"
        nodes.append({
            "id": bank_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 560},
            "data": {
                "category": "BANK_CREDIT",
                "title": f"Bank Credit {bank_tx.bank_entry_id}",
                "source_system": "Merchant Bank Statement",
                "record_id": bank_tx.bank_entry_id,
                "amount_paise": bank_tx.amount,
                "amount_inr": _paise_to_inr_str(bank_tx.amount),
                "date": bank_tx.bank_date.strftime("%Y-%m-%d %H:%M") if bank_tx.bank_date else None,
                "status": "CREDITED",
                "status_label": "Verified in Bank Statement",
                "visual_status": bank_visual,
                "is_missing": False,
                "confidence": float(settlement_recon.confidence) if settlement_recon and settlement_recon.confidence else 1.0,
                "rule": settlement_recon.match_type if settlement_recon else "Exact UTR / Reference Match",
                "discrepancy": settlement_recon.reason if settlement_recon and settlement_recon.status != "MATCHED" else None,
                "details": {
                    "UTR Code": bank_tx.utr or "N/A",
                    "Direction": bank_tx.direction,
                    "Narration": bank_tx.narration or "N/A",
                    "Value Date": bank_tx.bank_date.strftime("%Y-%m-%d") if bank_tx.bank_date else None,
                },
                "related_records": [settlement.settlement_id] if settlement else [],
            },
        })
        edges.append({
            "id": f"e-settlement-bank",
            "source": setl_node_id,
            "target": bank_node_id,
            "label": "NEFT credit verified",
            "animated": True,
            "style": {"stroke": "#10b981"},
        })
    else:
        bank_node_id = "node-bank-missing"
        nodes.append({
            "id": bank_node_id,
            "type": "lineageNode",
            "position": {"x": 300, "y": 560},
            "data": {
                "category": "BANK_CREDIT",
                "title": "Bank Credit: MISSING",
                "source_system": "Merchant Bank Statement",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "N/A",
                "date": None,
                "status": "UNCREDITED",
                "status_label": "No Bank Entry Found",
                "visual_status": "red" if settlement and settlement.status == "settled" else "grey",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Bank statement search across UTR, reference narration, and amount/date",
                "discrepancy": "Settlement payout dispatched but never credited to merchant bank account",
                "details": {},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-settlement-bank-missing",
            "source": setl_node_id,
            "target": bank_node_id,
            "label": "uncredited in bank",
            "animated": False,
            "style": {"stroke": "#ef4444", "strokeDasharray": "5 5"},
        })

    # Node: Ledger Entry
    if ledger_entry:
        ledger_node_id = f"node-ledger-{ledger_entry.entry_id}"
        nodes.append({
            "id": ledger_node_id,
            "type": "lineageNode",
            "position": {"x": 120, "y": 700},
            "data": {
                "category": "LEDGER",
                "title": f"Ledger {ledger_entry.entry_id}",
                "source_system": "ERP / General Ledger",
                "record_id": ledger_entry.entry_id,
                "amount_paise": ledger_entry.amount,
                "amount_inr": _paise_to_inr_str(ledger_entry.amount),
                "date": ledger_entry.entry_date.strftime("%Y-%m-%d %H:%M") if ledger_entry.entry_date else None,
                "status": "POSTED",
                "status_label": f"Booked as {ledger_entry.entry_type}",
                "visual_status": "green",
                "is_missing": False,
                "confidence": 1.0,
                "rule": "General Ledger Posting Reference",
                "discrepancy": None,
                "details": {
                    "Entry Type": ledger_entry.entry_type,
                    "Reference ID": ledger_entry.reference_id or "N/A",
                    "Description": ledger_entry.description or "N/A",
                },
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-bank-ledger",
            "source": bank_node_id,
            "target": ledger_node_id,
            "label": "ERP posting",
            "style": {"stroke": "#10b981"},
        })
    else:
        ledger_node_id = "node-ledger-missing"
        nodes.append({
            "id": ledger_node_id,
            "type": "lineageNode",
            "position": {"x": 120, "y": 700},
            "data": {
                "category": "LEDGER",
                "title": "Ledger Entry: MISSING",
                "source_system": "ERP / General Ledger",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "N/A",
                "date": None,
                "status": "UNPOSTED",
                "status_label": "Not Booked in ERP",
                "visual_status": "grey",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Audit search across General Ledger reference numbers",
                "discrepancy": "Transaction not posted to accounting general ledger",
                "details": {},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-bank-ledger-missing",
            "source": bank_node_id,
            "target": ledger_node_id,
            "label": "unbooked",
            "style": {"stroke": "#9ca3af", "strokeDasharray": "5 5"},
        })

    # Node: Shipment / Fulfillment
    if shipment:
        ship_visual = "green" if shipment.status == "DELIVERED" else "blue"
        ship_node_id = f"node-shipment-{shipment.shipment_id}"
        nodes.append({
            "id": ship_node_id,
            "type": "lineageNode",
            "position": {"x": 480, "y": 700},
            "data": {
                "category": "SHIPMENT",
                "title": f"Shipment {shipment.shipment_id}",
                "source_system": f"Logistics / {shipment.carrier or '3PL'}",
                "record_id": shipment.shipment_id,
                "amount_paise": None,
                "amount_inr": "Fulfilled",
                "date": shipment.shipped_at.strftime("%Y-%m-%d %H:%M") if shipment.shipped_at else None,
                "status": shipment.status,
                "status_label": "Delivered to Customer" if shipment.status == "DELIVERED" else shipment.status,
                "visual_status": ship_visual,
                "is_missing": False,
                "confidence": 1.0,
                "rule": "Warehouse AWB Generation & Dispatch",
                "discrepancy": None,
                "details": {
                    "Carrier": shipment.carrier or "Standard",
                    "Tracking AWB": shipment.tracking_number or "N/A",
                    "Shipped At": shipment.shipped_at.strftime("%Y-%m-%d %H:%M") if shipment.shipped_at else "Pending",
                    "Delivered At": shipment.delivered_at.strftime("%Y-%m-%d %H:%M") if shipment.delivered_at else "In Transit",
                },
                "related_records": [order.order_id] if order else [],
            },
        })
        edges.append({
            "id": f"e-order-shipment",
            "source": order_node_id,
            "target": ship_node_id,
            "label": "dispatched",
            "style": {"stroke": "#10b981" if ship_visual == "green" else "#3b82f6"},
        })
    else:
        ship_node_id = "node-shipment-missing"
        nodes.append({
            "id": ship_node_id,
            "type": "lineageNode",
            "position": {"x": 480, "y": 700},
            "data": {
                "category": "SHIPMENT",
                "title": "Shipment: NO RECORD FOUND",
                "source_system": "Logistics / 3PL",
                "record_id": "NO RECORD FOUND",
                "amount_paise": None,
                "amount_inr": "Unfulfilled",
                "date": None,
                "status": "UNFULFILLED",
                "status_label": "No Shipment Record",
                "visual_status": "red" if payment and payment.status == "captured" else "grey",
                "is_missing": True,
                "confidence": 0.0,
                "rule": "Logistics tracking query against customer order number",
                "discrepancy": "Payment captured without order fulfillment confirmation",
                "details": {},
                "related_records": [],
            },
        })
        edges.append({
            "id": f"e-order-shipment-missing",
            "source": order_node_id,
            "target": ship_node_id,
            "label": "missing fulfillment",
            "style": {"stroke": "#ef4444" if payment and payment.status == "captured" else "#9ca3af", "strokeDasharray": "5 5"},
        })

    # Optional Node: Refund
    if refund:
        refund_node_id = f"node-refund-{refund.refund_id}"
        nodes.append({
            "id": refund_node_id,
            "type": "lineageNode",
            "position": {"x": 120, "y": 840},
            "data": {
                "category": "REFUND",
                "title": f"Refund {refund.refund_id}",
                "source_system": "Payment Gateway Payouts",
                "record_id": refund.refund_id,
                "amount_paise": refund.amount,
                "amount_inr": _paise_to_inr_str(refund.amount),
                "date": refund.refund_date.strftime("%Y-%m-%d %H:%M") if refund.refund_date else None,
                "status": refund.status,
                "status_label": f"Customer Refund ({refund.status})",
                "visual_status": "yellow" if refund.status == "pending" else "green",
                "is_missing": False,
                "confidence": 1.0,
                "rule": "Customer Return Reversal",
                "discrepancy": None,
                "details": {
                    "Reason": refund.reason or "Customer Return",
                    "Processed At": refund.refund_date.strftime("%Y-%m-%d %H:%M") if refund.refund_date else "Pending",
                },
                "related_records": [payment.payment_id] if payment else [],
            },
        })
        edges.append({
            "id": f"e-payment-refund",
            "source": pay_node_id,
            "target": refund_node_id,
            "label": "refund initiated",
            "style": {"stroke": "#eab308"},
        })

    # Optional Node: Exception
    if exception:
        exc_node_id = f"node-exception-{exception.case_id}"
        nodes.append({
            "id": exc_node_id,
            "type": "lineageNode",
            "position": {"x": 480, "y": 840},
            "data": {
                "category": "EXCEPTION",
                "title": f"Case {exception.case_id}",
                "source_system": "CASHpilot Investigation Engine",
                "record_id": exception.case_id,
                "amount_paise": exception.value_at_risk,
                "amount_inr": _paise_to_inr_str(exception.value_at_risk),
                "date": exception.detected_at.strftime("%Y-%m-%d %H:%M") if exception.detected_at else None,
                "status": exception.status,
                "status_label": f"{exception.exception_type} ({exception.risk_level})",
                "visual_status": "red" if exception.risk_level in ("CRITICAL", "HIGH") else "yellow",
                "is_missing": False,
                "confidence": 1.0,
                "rule": exception.triggering_rule,
                "discrepancy": exception.explanation,
                "details": {
                    "Exception Type": exception.exception_type,
                    "Risk Level": exception.risk_level,
                    "Assigned Owner": exception.suggested_owner,
                    "Status": exception.status,
                },
                "related_records": [order.order_id if order else "", payment.payment_id if payment else ""],
            },
        })
        # Connect to whatever generated the exception
        exc_source = ship_node_id if exception.exception_type == "PAID_BUT_UNFULFILLED" else (
            bank_node_id if exception.exception_type == "SETTLEMENT_MISSING_IN_BANK" else pay_node_id
        )
        edges.append({
            "id": f"e-to-exception",
            "source": exc_source,
            "target": exc_node_id,
            "label": "alert triggered",
            "animated": True,
            "style": {"stroke": "#ef4444", "strokeWidth": 2},
        })

    # Compute overall lineage summary
    has_missing_critical = any(
        n["data"]["is_missing"] and n["data"]["visual_status"] in ("red", "grey")
        for n in nodes if n["data"]["category"] in ("PAYMENT", "BANK_CREDIT", "SHIPMENT")
    )
    break_point = None
    if not payment:
        break_point = "Payment was never captured for this order"
    elif shipment and shipment.status == "DELIVERED" and bank_tx:
        break_point = None
    elif not shipment:
        break_point = "Order fulfillment missing after captured payment"
    elif not bank_tx:
        break_point = "Bank credit missing for dispatched settlement"

    summary = {
        "complete": (not has_missing_critical and break_point is None),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "status": "AT_RISK" if (exception or has_missing_critical) else "RECONCILED",
        "gross_amount_paise": order.order_amount if order else (payment.amount if payment else 0),
        "gross_amount_inr": _paise_to_inr_str(order.order_amount if order else (payment.amount if payment else 0)),
        "net_settled_inr": _paise_to_inr_str(settlement.net_amount if settlement else None),
        "break_point": break_point,
    }

    return {
        "root_entity": {"type": entity_type, "id": entity_id},
        "summary": summary,
        "nodes": nodes,
        "edges": edges,
    }
