"""
Intent Classifier, Query Router, and Dispatcher for CashPilot AI.
"""
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas.ai import AssistantQueryResponse
from app.services.ai.sanitizer import sanitize_input
from app.services.ai.client import ai_client
from app.services.ai.evidence_builder import (
    build_settlement_evidence_package,
    build_missing_bank_evidence_package,
    build_unfulfilled_evidence_package,
    build_refund_ledger_evidence_package,
    build_cash_position_evidence_package,
    build_highest_risk_evidence_package,
    build_case_evidence_package,
    build_orders_evidence_package,
    build_bank_deposits_evidence_package,
    build_payment_gateways_evidence_package,
    build_exceptions_summary_evidence_package,
    build_tax_evidence_package,
    build_general_financial_evidence_package,
)

# Regex matching for entity mentions in queries
SETL_REGEX = re.compile(r'\b(SETL-\d+)\b', re.IGNORECASE)
CASE_REGEX = re.compile(r'\b(CASE-[A-Za-z0-9\-]+)\b', re.IGNORECASE)
ORDER_REGEX = re.compile(r'\b(ORD-\d+)\b', re.IGNORECASE)
REFUND_REGEX = re.compile(r'\b(REF-\d+)\b', re.IGNORECASE)


def detect_query_intent(query: str) -> Tuple[str, Optional[str]]:
    """
    Deterministically classifies the user query intent and extracts target entity IDs if any.
    Returns: (intent_name, entity_id_or_None)
    """
    q_lower = query.lower()

    # 1. Entity Lookups by ID
    case_match = CASE_REGEX.search(query)
    if case_match:
        return "CASE_EXPLANATION", case_match.group(1).upper()

    setl_match = SETL_REGEX.search(query)
    if setl_match:
        return "SETTLEMENT_EXPLANATION", setl_match.group(1).upper()

    order_match = ORDER_REGEX.search(query)
    if order_match:
        return "ORDER_EXPLANATION", order_match.group(1).upper()

    # 2. Paid unfulfilled query
    if any(k in q_lower for k in [
        "unfulfilled", "not fulfilled", "not shipped", "pending fulfillment",
        "delayed shipment", "unshipped", "paid but not shipped"
    ]) or ("paid" in q_lower and ("ship" in q_lower or "fulfill" in q_lower)):
        return "PAID_UNFULFILLED", None

    # 3. Missing in bank query (specifically missing / uncredited settlements)
    if ("bank" in q_lower and any(k in q_lower for k in ["missing", "uncredited", "delay", "not credited", "not in", "delayed"])) or "missing in bank" in q_lower:
        return "SETTLEMENT_MISSING_IN_BANK", None

    # 4. Bank Deposits / Statement balance query
    if any(k in q_lower for k in [
        "bank deposit", "bank deposits", "bank credit", "bank credits",
        "bank statement", "statement balance", "how much in bank", "statement entries",
        "bank transactions", "bank account", "bank inflow", "credited in bank",
        "deposit in bank", "deposits in bank", "total in bank"
    ]) or (q_lower.strip() in ["bank", "deposits", "bank deposits"]):
        return "BANK_DEPOSITS", None

    # 5. Orders Summary / Total Orders / Cart Volume query (handles typos like "totatal orders")
    if any(k in q_lower for k in [
        "total order", "total orders", "totatal orders", "totatal order", "order count",
        "order volume", "how many orders", "all orders", "cart orders", "sales volume",
        "orders by status", "order status", "orders"
    ]) or re.search(r'\b(order|orders)\b', q_lower):
        return "ORDERS_SUMMARY", None

    # 6. Payment Gateways / Methods query
    if any(k in q_lower for k in [
        "gateway", "gateways", "razorpay", "stripe", "phonepe",
        "captured payment", "captured payments", "payment method", "payment methods",
        "payment failure", "failed payments", "payment performance"
    ]):
        return "PAYMENT_GATEWAYS", None

    # 7. Refund missing in ledger / refunds status
    if any(k in q_lower for k in ["refund", "refunds", "returns"]) and any(k in q_lower for k in ["ledger", "accounting", "unposted", "journal", "books", "missing"]):
        return "REFUND_LEDGER_STATUS", None
    elif any(k in q_lower for k in ["refunds", "customer refund", "customer returns"]):
        return "REFUND_LEDGER_STATUS", None

    # 8. Highest risk items
    if any(k in q_lower for k in ["highest risk", "top risk", "critical", "most urgent", "priority exception", "worst", "highest value at risk"]):
        return "HIGHEST_RISK_ITEMS", None

    # 9. Exceptions & Anomalies Summary
    if any(k in q_lower for k in [
        "exception", "exceptions", "anomalies", "anomaly", "discrepancies",
        "discrepancy", "open cases", "unresolved cases", "how many exceptions",
        "all exceptions", "exception cases"
    ]):
        return "EXCEPTIONS_SUMMARY", None

    # 10. Tax / GST reconciliation
    if any(k in q_lower for k in ["tax", "gst", "tds", "input tax", "tax variance", "tax reconciliation"]):
        return "TAX_GST", None

    # 11. Cash position / liquidity arrival query
    if any(k in q_lower for k in [
        "cash position", "when will cash arrive", "expected cash", "liquidity",
        "cash balance", "cash posture", "cash flow", "cash in bank"
    ]):
        return "CASH_POSITION", None

    # 12. Settlement calculation question without specific ID
    if any(k in q_lower for k in ["settlement", "settlements", "gateway payout", "fee calculation", "mdr"]):
        return "SETTLEMENT_EXPLANATION", None

    return "GENERAL_FINANCE", None


def route_and_execute_query(db: Session, raw_query: str) -> AssistantQueryResponse:
    """
    Main entrypoint for AI Settlement Assistant queries.
    1. Sanitizes input
    2. Classifies intent
    3. Fetches verified deterministic evidence package
    4. Passes to AI client with fallback
    """
    clean_query = sanitize_input(raw_query)
    intent, entity_id = detect_query_intent(clean_query)

    # Fetch targeted evidence based on intent
    evidence_pkg = None

    if intent == "CASE_EXPLANATION" and entity_id:
        evidence_pkg = build_case_evidence_package(db, entity_id)

    elif intent == "SETTLEMENT_EXPLANATION":
        target_id = entity_id or "SETL-9001"
        evidence_pkg = build_settlement_evidence_package(db, target_id)
        if not evidence_pkg:
            evidence_pkg = build_settlement_evidence_package(db, "SETL-9019")

    elif intent == "ORDER_EXPLANATION" and entity_id:
        evidence_pkg = build_orders_evidence_package(db, entity_id)

    elif intent == "ORDERS_SUMMARY":
        evidence_pkg = build_orders_evidence_package(db, None)

    elif intent == "BANK_DEPOSITS":
        evidence_pkg = build_bank_deposits_evidence_package(db)

    elif intent == "PAYMENT_GATEWAYS":
        evidence_pkg = build_payment_gateways_evidence_package(db)

    elif intent == "EXCEPTIONS_SUMMARY":
        evidence_pkg = build_exceptions_summary_evidence_package(db)

    elif intent == "TAX_GST":
        evidence_pkg = build_tax_evidence_package(db)

    elif intent == "SETTLEMENT_MISSING_IN_BANK":
        evidence_pkg = build_missing_bank_evidence_package(db)

    elif intent == "PAID_UNFULFILLED":
        evidence_pkg = build_unfulfilled_evidence_package(db)

    elif intent == "REFUND_LEDGER_STATUS":
        evidence_pkg = build_refund_ledger_evidence_package(db)

    elif intent == "CASH_POSITION":
        evidence_pkg = build_cash_position_evidence_package(db)

    elif intent == "HIGHEST_RISK_ITEMS":
        evidence_pkg = build_highest_risk_evidence_package(db, limit=5)

    elif intent == "GENERAL_FINANCE":
        evidence_pkg = build_general_financial_evidence_package(db)

    # Fallback if package could not be retrieved
    if not evidence_pkg:
        evidence_pkg = build_general_financial_evidence_package(db)
        intent = "GENERAL_FINANCE"

    # Execute assistant generation
    return ai_client.answer_assistant_query(clean_query, evidence_pkg, intent)

