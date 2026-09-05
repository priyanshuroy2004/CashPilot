"""
Column-name mapper for CASHpilot AI CSV ingestion.

Maps arbitrary column names from uploaded CSV files to canonical column names
using deterministic alias dictionaries.  No machine-learning is required.

Usage
-----
from app.services.schema_normalizer.mapper import map_columns, DATASET_REQUIRED

mapping, unmapped = map_columns(raw_columns, dataset_type="orders")
# mapping  → {"Order No.": "order_id", "Total": "order_amount", ...}
# unmapped → ["SomeUnknownCol", ...]
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Alias dictionary
# Each key is a canonical column name.
# Each value is a list of lower-cased, whitespace-normalised aliases.
# ---------------------------------------------------------------------------
_ALIASES: Dict[str, Dict[str, List[str]]] = {
    # ── ORDERS ──────────────────────────────────────────────────────────────
    "orders": {
        "order_id": [
            "order_id", "order_number", "order_no", "order no", "order no.",
            "orderid", "order ref", "order_ref", "order id", "order#",
            "order number", "order_num",
        ],
        "customer_id": [
            "customer_id", "customer_no", "cust_id", "buyer_id",
            "customer id", "customer", "client_id", "user_id",
        ],
        "order_amount": [
            "order_amount", "total", "total_amount", "order_total",
            "grand_total", "sale_amount", "invoice_amount", "value",
            "order value", "amount",
        ],
        "currency": ["currency", "currency_code", "ccy"],
        "order_date": [
            "order_date", "order_datetime", "date_created", "date created",
            "created_at", "created_on", "order time", "placed_on", "date",
        ],
        "payment_mode": [
            "payment_mode", "payment_method", "mode", "pay_mode", "payment mode",
        ],
        "order_status": [
            "order_status", "status", "state", "order state",
        ],
    },

    # ── PAYMENTS ─────────────────────────────────────────────────────────────
    "payments": {
        "payment_id": [
            "payment_id", "transaction_id", "txn_id", "pay_id",
            "payment_ref", "txn_ref", "transaction id", "payment ref",
            "trans_id", "pg_ref", "razorpay_payment_id", "payment id",
        ],
        "order_id": [
            "order_id", "order_number", "order_ref", "order no", "order id",
        ],
        "amount": [
            "amount", "payment_amount", "txn_amount", "transaction_amount",
            "paid_amount", "payment amount",
        ],
        "currency": ["currency", "currency_code"],
        "status": [
            "status", "payment_status", "txn_status", "transaction_status",
        ],
        "payment_method": [
            "payment_method", "payment_mode", "method", "mode", "pay_method",
        ],
        "payment_captured_at": [
            "payment_captured_at", "captured_at", "capture_date", "paid_at",
            "payment_date", "capture_time", "settled_at",
        ],
    },

    # ── SETTLEMENTS ──────────────────────────────────────────────────────────
    "settlements": {
        "settlement_id": [
            "settlement_id", "settlement_no", "setl_id", "settlement id",
            "setl no", "settlement number", "razorpay_settlement_id",
        ],
        "settlement_date": [
            "settlement_date", "settled_on", "settlement_datetime",
            "settlement date", "date",
        ],
        "gross_amount": [
            "gross_amount", "gross", "gross_settlement", "total_amount",
            "gross amount", "settlement_gross",
        ],
        "fee_amount": [
            "fee_amount", "fee", "platform_fee", "charges", "processing_fee",
        ],
        "tax_amount": [
            "tax_amount", "tax", "gst", "gst_amount", "tax on fee",
        ],
        "adjustment_amount": [
            "adjustment_amount", "adjustment", "adj_amount", "adjustments",
        ],
        "net_amount": [
            "net_amount", "net", "net_settlement", "net_payout",
            "net amount", "amount_settled",
        ],
        "settlement_utr": [
            "settlement_utr", "utr", "utr_number", "bank_ref", "reference",
            "transaction_ref", "neft_ref", "rtgs_ref",
        ],
        "status": ["status", "settlement_status"],
    },

    # ── SETTLEMENT LINES ─────────────────────────────────────────────────────
    "settlement_lines": {
        "settlement_id": [
            "settlement_id", "settlement_no", "setl_id", "settlement id",
        ],
        "payment_id": [
            "payment_id", "transaction_id", "txn_id", "pay_id", "payment id",
        ],
        "amount": [
            "amount", "payment_amount", "gross_amount", "gross",
        ],
        "fee": ["fee", "fee_amount", "platform_fee"],
        "tax": ["tax", "tax_amount", "gst"],
        "net_amount": ["net_amount", "net", "net_payment"],
    },

    # ── BANK TRANSACTIONS ────────────────────────────────────────────────────
    "bank_transactions": {
        "bank_entry_id": [
            "bank_entry_id", "entry_id", "ref_no", "bank_ref", "sl_no",
            "serial", "serial_no", "chq_no", "cheque_no",
            "transaction_reference", "sr_no",
        ],
        "bank_date": [
            "bank_date", "transaction_date", "value_date", "txn_date",
            "date", "posting_date",
        ],
        "amount": [
            "amount", "transaction_amount", "txn_amount",
            "debit_credit_amount", "cr_dr_amount",
        ],
        "direction": [
            "direction", "dr_cr", "debit_credit", "type",
            "transaction_type_indicator", "cr_dr", "drcr",
        ],
        "narration": [
            "narration", "description", "remarks", "particulars",
            "details", "transaction_details", "memo",
        ],
        "utr": [
            "utr", "utr_number", "reference", "bank_ref",
            "remittance_ref", "transaction_ref", "ref",
        ],
        "transaction_type": [
            "transaction_type", "type", "category", "trans_type",
        ],
    },
}

# Canonical required columns per dataset type (used by validator)
DATASET_REQUIRED: Dict[str, List[str]] = {
    "orders":            ["order_id", "order_amount", "order_date", "order_status"],
    "payments":          ["payment_id", "amount", "status"],
    "settlements":       ["settlement_id", "gross_amount", "fee_amount",
                          "tax_amount", "net_amount", "settlement_date"],
    "settlement_lines":  ["settlement_id", "payment_id", "amount", "fee", "tax", "net_amount"],
    "bank_transactions": ["bank_entry_id", "bank_date", "amount", "direction"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise_key(col: str) -> str:
    """Lower-case, strip, collapse whitespace / punctuation to underscores."""
    col = col.strip().lower()
    col = re.sub(r"[\s\-/\.]+", "_", col)  # spaces, dashes, slashes, dots → _
    col = re.sub(r"[^a-z0-9_]", "", col)   # remove any other non-alnum
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def _build_lookup(dataset_type: str) -> Dict[str, str]:
    """Build alias→canonical lookup for a specific dataset type."""
    lookup: Dict[str, str] = {}
    for canonical, aliases in _ALIASES.get(dataset_type, {}).items():
        for alias in aliases:
            lookup[_normalise_key(alias)] = canonical
    return lookup


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def map_columns(
    raw_columns: List[str],
    dataset_type: str,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Map *raw_columns* to canonical column names for *dataset_type*.

    Returns
    -------
    mapping  : dict  {original_col_name → canonical_name}
    unmapped : list  [original_col_names that could not be mapped]
    """
    lookup = _build_lookup(dataset_type)
    mapping: Dict[str, str] = {}
    unmapped: List[str] = []

    # Track which canonical cols have already been claimed (first-match wins)
    claimed: set[str] = set()

    for col in raw_columns:
        key = _normalise_key(col)
        canonical = lookup.get(key)
        if canonical and canonical not in claimed:
            mapping[col] = canonical
            claimed.add(canonical)
        else:
            unmapped.append(col)

    return mapping, unmapped


def mapping_confidence(mapping: Dict[str, str], dataset_type: str) -> str:
    """Return HIGH / MEDIUM / LOW based on required column coverage."""
    required = set(DATASET_REQUIRED.get(dataset_type, []))
    if not required:
        return "LOW"
    mapped_canonical = set(mapping.values())
    covered = required & mapped_canonical
    ratio = len(covered) / len(required)
    if ratio == 1.0:
        return "HIGH"
    elif ratio >= 0.5:
        return "MEDIUM"
    return "LOW"
