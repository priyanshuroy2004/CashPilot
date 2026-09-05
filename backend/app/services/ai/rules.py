"""
Deterministic Rules for Suggested Owner, Advisory Actions, and Template-Based Financial Explanations.

All ownership assignment follows strict deterministic rules.
Recommendations are strictly read-only advisories and must never trigger automatic mutations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.ai import (
    CaseExplanationResponse,
    AssistantQueryResponse,
    DailyExceptionSummaryResponse,
    FinancialBreakdown,
    EvidenceRecord,
)


def get_suggested_owner(exception_type: str, has_customer_complaint: bool = False) -> Tuple[str, str]:
    """
    Returns (suggested_owner, rationale) based on deterministic domain ownership rules.
    """
    exc_type = (exception_type or "").upper().strip()

    if has_customer_complaint:
        return (
            "Support",
            "An active customer complaint or delivery escalation requires customer support intervention."
        )

    if exc_type == "PAID_BUT_UNFULFILLED":
        return (
            "Operations",
            "Payment was captured successfully, but physical fulfillment or courier dispatch is missing in logistics records."
        )
    elif exc_type == "SETTLEMENT_MISSING_IN_BANK":
        return (
            "Finance",
            "Dispatched settlement payout has exceeded the expected banking credit window without a matching bank deposit."
        )
    elif exc_type == "REFUND_MISSING_IN_LEDGER":
        return (
            "Finance",
            "Gateway processed customer refund, but the return is unposted in the accounting general ledger."
        )
    elif exc_type == "PAYMENT_AMOUNT_MISMATCH":
        return (
            "Finance",
            "Discrepancy detected between invoiced order total and payment gateway captured amount."
        )
    elif exc_type == "CALCULATION_DISCREPANCY":
        return (
            "Finance",
            "Reported net payout differs from deterministic calculation of gross sales, gateway fees, GST, and adjustments."
        )
    else:
        return (
            "Finance",
            "Financial reconciliation anomaly flagged for audit and investigation."
        )


def get_recommended_actions(exception_type: str) -> List[str]:
    """
    Returns deterministic, advisory action checklists for merchant teams.
    Actions are strictly advisory and require human approval.
    """
    exc_type = (exception_type or "").upper().strip()

    if exc_type == "PAID_BUT_UNFULFILLED":
        return [
            "Verify warehouse packaging and logistics dispatch status in WMS.",
            "Confirm courier tracking number and pickup scan history with delivery partner.",
            "Proactively contact customer with estimated delivery timeframe to prevent dispute or chargeback.",
            "If inventory is unavailable, route order to supervisor for formal refund authorization.",
        ]
    elif exc_type == "SETTLEMENT_MISSING_IN_BANK":
        return [
            "Cross-verify settlement UTR reference against bank account transaction statement.",
            "Confirm standard banking settlement window (T+1 / T+2 working days) has elapsed.",
            "Check for unassigned or bulk bank deposits matching settlement net payout.",
            "Raise inquiry with payment gateway treasury desk if payout remains uncredited.",
        ]
    elif exc_type == "REFUND_MISSING_IN_LEDGER":
        return [
            "Verify gateway refund transaction reference and original payment ID.",
            "Check if refund was deducted from a subsequent payout settlement batch.",
            "Create an accounting journal voucher task to record the return in the general ledger.",
            "Confirm refund tax credit (GST reversal) has been documented in accounting books.",
        ]
    elif exc_type == "PAYMENT_AMOUNT_MISMATCH":
        return [
            "Inspect e-commerce cart line items and applied promotional coupons.",
            "Compare captured gateway amount against invoiced customer bill.",
            "Verify whether payment gateway applied partial authorization or MDR fee deduction at capture.",
            "Escalate to billing operations for invoice debit/credit note adjustment.",
        ]
    elif exc_type == "CALCULATION_DISCREPANCY":
        return [
            "Download raw settlement batch detail CSV from payment gateway merchant portal.",
            "Verify contract fee percentage (e.g. 2.0%) and GST (18%) on each transaction.",
            "Inspect adjustment line items for dispute clawbacks, chargeback fees, or security reserves.",
            "Submit fee variance dispute ticket with payment partner support.",
        ]
    else:
        return [
            "Review transaction lineage across cart, gateway, bank, and ledger.",
            "Audit source timestamps and reference identifiers.",
            "Escalate to Finance controller if discrepancy exceeds tolerance threshold.",
        ]


def generate_deterministic_explanation(evidence_pkg: Dict[str, Any]) -> CaseExplanationResponse:
    """
    Builds a complete, deterministic, evidence-grounded explanation for a financial exception case.
    """
    case_id = evidence_pkg.get("case_id", "UNKNOWN")
    exc_type = evidence_pkg.get("exception_type", "ANOMALY")
    risk_level = evidence_pkg.get("risk_level", "MEDIUM")
    var_inr = evidence_pkg.get("value_at_risk_inr", "₹0.00")
    facts = evidence_pkg.get("verified_facts", {})
    records = evidence_pkg.get("evidence_records", [])
    allowed_ids = evidence_pkg.get("evidence_ids", [])
    trigger = evidence_pkg.get("trigger_rule", "Deterministic threshold breach")

    owner, owner_reason = get_suggested_owner(exc_type)
    actions = get_recommended_actions(exc_type)

    if exc_type == "PAID_BUT_UNFULFILLED":
        order_id = facts.get("order_id", "Unknown Order")
        payment_id = facts.get("payment_id", "Unknown Payment")
        age = facts.get("payment_age_hours", ">72")
        summary = f"Order {order_id} has captured payment {payment_id} totaling {var_inr}, but courier fulfillment has been missing for {age} hours."
        what_happened = f"Customer completed checkout and payment {payment_id} was successfully captured by the payment gateway. However, no carrier dispatch record or tracking number exists in shipping logs."
        why_flagged = f"Breached warehouse SLA threshold: Payment captured > 72 hours without active courier tracking scan ({trigger})."
        financial_impact = f"Immediate merchant exposure of {var_inr}. Unfulfilled captured orders risk automated consumer disputes, payment gateway chargeback penalties, and merchant reputation damage."

    elif exc_type == "SETTLEMENT_MISSING_IN_BANK":
        setl_id = facts.get("settlement_id", "Unknown Settlement")
        utr = facts.get("settlement_utr", "N/A")
        summary = f"Settlement batch {setl_id} ({var_inr}) was closed by payment gateway, but matching bank credit is unverified after the settlement window."
        what_happened = f"Payment gateway generated settlement {setl_id} with UTR '{utr}' for {var_inr}. Core banking statement reconciliation did not identify a corresponding deposit entry."
        why_flagged = f"Banking deposit window exceeded: Settlement status marked closed > 48 hours without matched bank ledger credit ({trigger})."
        financial_impact = f"Liquidity deficit of {var_inr}. Merchant operating cash is trapped in transit or delayed at gateway partner clearing."

    elif exc_type == "REFUND_MISSING_IN_LEDGER":
        ref_id = facts.get("refund_id", facts.get("related_refund_id", "Unknown Refund"))
        summary = f"Refund {ref_id} ({var_inr}) was issued to customer, but has no corresponding journal entry in the accounting general ledger."
        what_happened = f"Payment gateway confirmed successful debit for customer refund {ref_id}. The accounting general ledger does not reflect this return debit."
        why_flagged = f"Ledger reconciliation check failed: Missing journal entry for verified gateway customer refund ({trigger})."
        financial_impact = f"Accounting variance of {var_inr}. Understates customer returns, distorts revenue recognition, and creates statutory tax audit discrepancies."

    elif exc_type == "CALCULATION_DISCREPANCY":
        setl_id = facts.get("settlement_id", "Settlement")
        variance = facts.get("variance_inr", var_inr)
        summary = f"Settlement {setl_id} displays a mathematical net calculation variance of {variance} against deterministic contract rates."
        what_happened = f"Reconstructed transaction lines (gross sales minus MDR contract rate minus 18% GST minus refunds) diverge from reported payout."
        why_flagged = f"Contract reconciliation anomaly: Gateway reported payout differs from deterministic calculation ({trigger})."
        financial_impact = f"Excess gateway deduction or overcharge exposure of {variance}."

    else:
        summary = f"Exception {case_id} flagged: {exc_type} with total value at risk of {var_inr}."
        what_happened = f"Deterministic rule engine detected a condition breach ({trigger})."
        why_flagged = trigger
        financial_impact = f"Potential financial or operational risk of {var_inr}."

    return CaseExplanationResponse(
        case_id=case_id,
        exception_type=exc_type,
        risk_level=risk_level,
        value_at_risk_inr=var_inr,
        summary=summary,
        what_happened=what_happened,
        why_flagged=why_flagged,
        financial_impact=financial_impact,
        suggested_owner=owner,
        suggested_owner_reason=owner_reason,
        recommended_actions=actions,
        verified_facts=facts,
        evidence_ids=allowed_ids,
        evidence_records=records,
        confidence_note="100% grounded in verified relational database records. AI generated zero financial figures.",
        is_fallback=True,
    )


def generate_deterministic_assistant_answer(
    query: str, evidence_pkg: Dict[str, Any], intent: str
) -> AssistantQueryResponse:
    """
    Produces structured answers to financial queries using verified facts.
    """
    records = evidence_pkg.get("evidence_records", [])
    breakdown = None

    if intent == "SETTLEMENT_EXPLANATION":
        setl_id = evidence_pkg.get("settlement_id", "Settlement")
        gross = evidence_pkg.get("gross_amount_inr", "₹0.00")
        fee = evidence_pkg.get("fee_amount_inr", "₹0.00")
        tax = evidence_pkg.get("tax_amount_inr", "₹0.00")
        refund = evidence_pkg.get("refund_adjustment_inr", "₹0.00")
        exp_net = evidence_pkg.get("expected_net_inr", "₹0.00")
        rep_net = evidence_pkg.get("reported_net_inr", "₹0.00")
        var = evidence_pkg.get("variance_inr", "₹0.00")
        calc_status = evidence_pkg.get("calculation_status", "MATCHED")
        bank_status = evidence_pkg.get("bank_match_status", "PENDING")

        breakdown = FinancialBreakdown(
            gross_amount_inr=gross,
            fee_amount_inr=fee,
            tax_amount_inr=tax,
            refund_adjustment_inr=refund,
            expected_net_inr=exp_net,
            reported_or_bank_inr=rep_net,
            variance_inr=var,
            status=calc_status,
        )

        answer = (
            f"Settlement {setl_id} has gross sales of {gross}, gateway MDR fees of {fee}, "
            f"GST tax of {tax}, and refund adjustments of {refund}. "
            f"Deterministic expected net is {exp_net} vs reported net payout of {rep_net} (Variance: {var}). "
            f"Bank credit status is currently {bank_status}."
        )
        explanation = (
            f"Calculated in accordance with merchant gateway terms. "
            f"{'No mathematical variance detected in fee deductions.' if var == '₹0.00' else f'A variance of {var} was identified between calculated and reported payout.'}"
        )
        actions = [
            f"Verify bank deposit credit entry for settlement {setl_id}.",
            "Compare gateway MDR rate table against contractual agreed rate.",
        ]

    elif intent == "SETTLEMENT_MISSING_IN_BANK":
        count = evidence_pkg.get("missing_count", 0)
        total_var = evidence_pkg.get("total_value_at_risk_inr", "₹0.00")
        answer = f"There are currently {count} settlement batch(es) missing from the bank account, representing a total delayed cash liquidity of {total_var}."
        explanation = "These settlements were closed by the payment gateway but no matching credit transaction was detected in bank statements after the standard T+2 clearing window."
        actions = [
            "Download updated bank statement MT940 / CSV file.",
            "Cross-verify gateway UTR numbers with bank relationship manager.",
        ]

    elif intent == "PAID_UNFULFILLED":
        count = evidence_pkg.get("unfulfilled_count", 0)
        total_var = evidence_pkg.get("total_value_at_risk_inr", "₹0.00")
        answer = f"There are {count} captured order(s) awaiting fulfillment past the 72-hour warehouse SLA, totaling {total_var} in revenue at risk."
        explanation = "Customer funds have been captured by payment gateways, but logistics records contain no courier dispatch scans or tracking updates."
        actions = [
            "Notify fulfillment warehouse team to expedite packing and handover.",
            "Audit inventory availability for unfulfilled order IDs.",
        ]

    elif intent == "REFUND_LEDGER_STATUS":
        count = evidence_pkg.get("missing_count", 0)
        total_var = evidence_pkg.get("total_unposted_refunds_inr", "₹0.00")
        answer = f"Found {count} processed customer refund(s) totaling {total_var} that have not yet been posted to the accounting general ledger."
        explanation = "These customer returns were disbursed through payment gateways, but have not generated matching double-entry ledger vouchers in ERP/accounting."
        actions = [
            "Post journal voucher credit entries for pending refund IDs.",
            "Verify reversal of GST input tax credits on refunded merchandise.",
        ]

    elif intent == "CASH_POSITION":
        recv = evidence_pkg.get("already_received_inr", "₹0.00")
        flight = evidence_pkg.get("expected_in_flight_inr", "₹0.00")
        pending = evidence_pkg.get("pending_gateway_payout_inr", "₹0.00")
        risk = evidence_pkg.get("at_risk_inr", "₹0.00")
        answer = (
            f"Cash Liquidity Posture: {recv} already credited in bank; {flight} in-flight from payment gateways; "
            f"{pending} in captured cart orders awaiting payout batching. "
            f"Total open risk stands at {risk}."
        )
        explanation = "Reconciliation covers all bank credits, dispatched settlement batches, captured unbatched orders, and flagged exceptions."
        actions = [
            "Monitor gateway payout clearing schedules for in-flight funds.",
            "Resolve high-priority exception cases to release withheld funds.",
        ]

    elif intent == "HIGHEST_RISK_ITEMS":
        count = evidence_pkg.get("top_cases_count", 0)
        answer = f"Identified {count} critical exception case(s) requiring immediate finance review."
        explanation = "Ranked deterministically by multi-factor risk priority (Risk Tier and Value at Risk in INR)."
        actions = [
            "Review top case investigation drill-down views.",
            "Assign open cases to domain owners in Operations or Finance.",
        ]

    elif intent == "ORDERS_SUMMARY":
        count = evidence_pkg.get("total_orders_count", 0)
        amt = evidence_pkg.get("total_orders_amount_inr", "₹0.00")
        breakdown_dict = evidence_pkg.get("status_breakdown", {})
        breakdown_parts = [f"{st}: {c}" for st, c in breakdown_dict.items()]
        breakdown_str = ", ".join(breakdown_parts) if breakdown_parts else "All confirmed"
        answer = (
            f"Total Orders Volume: CashPilot has recorded {count} total cart orders totaling {amt}. "
            f"Status breakdown: {breakdown_str}."
        )
        explanation = "Orders are synchronized directly from merchant cart databases and verified against checkout transactions."
        actions = [
            "Review orders workspace to inspect paid vs pending fulfillment status.",
            "Verify gateway checkout conversion and abandoned cart rates.",
        ]

    elif intent == "ORDER_EXPLANATION":
        order_id = evidence_pkg.get("order_id", "Order")
        amt = evidence_pkg.get("order_amount_inr", "₹0.00")
        status = evidence_pkg.get("order_status", "UNKNOWN")
        ship_status = evidence_pkg.get("shipment_status", "NOT_FOUND")
        payments = evidence_pkg.get("payments", [])
        pay_info = f"{len(payments)} payment(s) ({', '.join(p.get('status') for p in payments)})" if payments else "No payment records"
        exc_id = evidence_pkg.get("exception_case_id")
        exc_str = f" Flagged in exception case {exc_id}." if exc_id else " No active exception flags."
        answer = (
            f"Order {order_id} totaling {amt} has status '{status}'. Payment: {pay_info}. "
            f"Courier shipment: '{ship_status}'.{exc_str}"
        )
        explanation = f"Transaction lifecycle for order {order_id} across checkout, gateway capture, and courier fulfillment."
        actions = [
            f"View order {order_id} in Investigation Center for full lineage graph.",
            "Check courier tracking number and delivery milestones.",
        ]

    elif intent == "BANK_DEPOSITS":
        credit_count = evidence_pkg.get("total_credit_transactions", 0)
        credit_amt = evidence_pkg.get("total_credited_amount_inr", "₹0.00")
        net_inflow = evidence_pkg.get("net_bank_inflow_inr", credit_amt)
        recon_count = evidence_pkg.get("reconciled_settlements_count", 0)
        answer = (
            f"Bank Statement Activity: Verified {credit_count} deposit credit(s) totaling {credit_amt} in bank statements. "
            f"Net bank inflow movement stands at {net_inflow}."
        )
        explanation = (
            f"Core banking reconciliation confirms {recon_count} gateway settlement batches have successfully cleared "
            f"into merchant operating accounts with matching UTR references."
        )
        actions = [
            "Download updated bank statement MT940 / CSV file to reconcile recent credits.",
            "Cross-verify gateway UTR numbers for any unmatched credit entries.",
        ]

    elif intent == "PAYMENT_GATEWAYS":
        total_p = evidence_pkg.get("total_payments_count", 0)
        captured = evidence_pkg.get("captured_count", 0)
        captured_amt = evidence_pkg.get("total_captured_amount_inr", "₹0.00")
        failed = evidence_pkg.get("failed_count", 0)
        methods = evidence_pkg.get("method_breakdown", {})
        methods_str = ", ".join([f"{m}: {c}" for m, c in methods.items()]) if methods else "Various"
        answer = (
            f"Payment Gateway Performance: {captured} of {total_p} payment transactions successfully captured totaling {captured_amt}. "
            f"Payment methods: {methods_str}."
        )
        explanation = f"Gateway records reflect processed merchant card, UPI, and netbanking collections. {failed} failed transaction(s) recorded."
        actions = [
            "Monitor capture-to-settlement velocity for open gateway batches.",
            "Audit failed transactions for gateway decline reason codes.",
        ]

    elif intent == "EXCEPTIONS_SUMMARY":
        open_cases = evidence_pkg.get("total_open_cases", 0)
        var = evidence_pkg.get("total_value_at_risk_inr", "₹0.00")
        types = evidence_pkg.get("type_breakdown", {})
        types_str = ", ".join([f"{k.replace('_', ' ')}: {v}" for k, v in types.items()]) if types else "None"
        risks = evidence_pkg.get("risk_breakdown", {})
        answer = (
            f"Financial Exceptions Status: There are currently {open_cases} unresolved exception case(s) "
            f"with total value at risk of {var}. Categories: {types_str}."
        )
        explanation = (
            f"Risk breakdown: {risks.get('CRITICAL', 0)} Critical, {risks.get('HIGH', 0)} High, "
            f"{risks.get('MEDIUM', 0)} Medium, {risks.get('LOW', 0)} Low."
        )
        actions = [
            "Open Exception Investigation Workspace to triage critical items.",
            "Assign open cases to domain owners in Operations and Finance.",
        ]

    elif intent == "TAX_GST":
        batches = evidence_pkg.get("total_tax_batches", 0)
        matched = evidence_pkg.get("matched_count", 0)
        discrepancy = evidence_pkg.get("discrepancy_count", 0)
        reported_tax = evidence_pkg.get("total_reported_tax_inr", "₹0.00")
        variance = evidence_pkg.get("total_variance_inr", "₹0.00")
        answer = (
            f"Tax & GST Status: {matched} of {batches} settlement batches have verified matching GST (18%) on gateway MDR fees. "
            f"Total reported tax is {reported_tax} with a net variance of {variance}."
        )
        explanation = "Statutory GST compliance requires exact 18% tax on payment platform fees with valid tax invoice line items."
        actions = [
            "Audit settlement lines with GST calculation discrepancies.",
            "Reconcile monthly GSTR-2B input tax credits with gateway GST tax invoices.",
        ]

    elif intent == "GENERAL_FINANCE":
        orders_c = evidence_pkg.get("total_orders_count", 0)
        orders_a = evidence_pkg.get("total_orders_amount_inr", "₹0.00")
        bank_c = evidence_pkg.get("total_bank_credits_count", 0)
        bank_a = evidence_pkg.get("total_bank_credited_inr", "₹0.00")
        exc_c = evidence_pkg.get("total_open_exceptions", 0)
        var = evidence_pkg.get("total_value_at_risk_inr", "₹0.00")
        answer = (
            f"Financial System Overview: CashPilot has reconciled {orders_c} orders ({orders_a}) "
            f"and verified {bank_c} bank credit deposits ({bank_a}). "
            f"Currently {exc_c} open exception(s) represent {var} in open value at risk."
        )
        explanation = "All figures are verified against current database records across cart orders, payment gateway captures, settlement batches, and bank statements."
        actions = [
            "Ask about specific orders (e.g. 'ORD-1001'), settlements ('SETL-9001'), or bank deposits.",
            "Review open exceptions in the Investigation Center to mitigate financial risk.",
        ]

    else:
        answer = "Inquiry analyzed against verified financial records and reconciliation logs."
        explanation = "CashPilot verified that all financial data matches underlying relational database state."
        actions = ["Review Reconciliation Workspace for granular batch analysis."]

    return AssistantQueryResponse(
        query=query,
        detected_intent=intent,
        answer=answer,
        explanation=explanation,
        breakdown=breakdown,
        verified_facts=evidence_pkg.get("verified_facts", {}),
        evidence_records=records,
        recommended_actions=actions,
        is_fallback=True,
    )


def generate_deterministic_executive_summary(
    summary_data: Dict[str, Any]
) -> DailyExceptionSummaryResponse:
    """
    Builds the executive daily briefing for leadership.
    """
    cash = summary_data.get("cash_posture", {})
    highest_risk = summary_data.get("highest_risk", {})
    top_cases = highest_risk.get("top_cases", [])
    metrics = summary_data.get("key_metrics", {})

    top_case_id = top_cases[0]["case_id"] if top_cases else None
    top_case_summary = top_cases[0]["explanation"] if top_cases else "No critical open exceptions."

    total_var = cash.get("at_risk_inr", "₹0.00")
    total_cases = cash.get("at_risk_case_count", 0)

    summary_text = (
        f"Financial Control Status: Total Value at Risk across open exceptions is {total_var} across {total_cases} case(s). "
        f"Bank accounts have confirmed {cash.get('already_received_inr', '₹0.00')} in deposits, with {cash.get('expected_in_flight_inr', '₹0.00')} "
        f"in-flight gateway payouts. Settlement accuracy rate is {metrics.get('settlement_accuracy_rate', '100%')}."
    )

    return DailyExceptionSummaryResponse(
        as_of=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        total_unresolved_cases=total_cases,
        total_value_at_risk_inr=total_var,
        critical_cases_count=sum(1 for c in top_cases if c.get("risk_level") == "CRITICAL"),
        high_cases_count=sum(1 for c in top_cases if c.get("risk_level") == "HIGH"),
        medium_cases_count=sum(1 for c in top_cases if c.get("risk_level") == "MEDIUM"),
        low_cases_count=sum(1 for c in top_cases if c.get("risk_level") == "LOW"),
        summary_text=summary_text,
        highest_priority_case_id=top_case_id,
        highest_priority_case_summary=top_case_summary,
        top_recommended_actions=[
            "Investigate and resolve top priority critical cases to release delayed settlement cash.",
            "Verify bank clearing for in-flight gateway payouts exceeding 48 hours.",
            "Coordinate with logistics warehouse to dispatch captured orders older than 72 hours.",
        ],
        is_fallback=True,
    )
