"""
CSV validator for CASHpilot AI.

Validates an uploaded CSV after column normalization.  Returns:
- valid rows (as list of dicts with canonical column names)
- validation errors  (row number, field, message)

Rules per dataset type:
  - required columns present
  - no null primary identifiers
  - duplicate primary keys flagged
  - numeric amount fields parse to positive integers (paise)
  - date fields parse to valid datetime
  - status / direction fields restricted to known values
  - amounts stored as BIGINT paise; rupee decimals auto-converted
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.services.schema_normalizer.mapper import DATASET_REQUIRED

# ---------------------------------------------------------------------------
# Validation rules per dataset
# ---------------------------------------------------------------------------
_NUMERIC_COLS: Dict[str, List[str]] = {
    "orders":            ["order_amount"],
    "payments":          ["amount"],
    "settlements":       ["gross_amount", "fee_amount", "tax_amount",
                          "adjustment_amount", "net_amount"],
    "settlement_lines":  ["amount", "fee", "tax", "net_amount"],
    "bank_transactions": ["amount"],
}

_DATE_COLS: Dict[str, List[str]] = {
    "orders":            ["order_date"],
    "payments":          ["payment_captured_at"],  # optional
    "settlements":       ["settlement_date"],
    "settlement_lines":  [],
    "bank_transactions": ["bank_date"],
}

_DATE_REQUIRED: Dict[str, List[str]] = {
    "orders":            ["order_date"],
    "payments":          [],   # payment_captured_at is optional
    "settlements":       ["settlement_date"],
    "settlement_lines":  [],
    "bank_transactions": ["bank_date"],
}

_PRIMARY_KEY: Dict[str, Optional[str]] = {
    "orders":            "order_id",
    "payments":          "payment_id",
    "settlements":       "settlement_id",
    "settlement_lines":  None,   # composite key checked separately
    "bank_transactions": "bank_entry_id",
}

_STATUS_COLS: Dict[str, Optional[str]] = {
    "orders":            "order_status",
    "payments":          "status",
    "settlements":       "status",
    "settlement_lines":  None,
    "bank_transactions": "direction",
}

_VALID_STATUSES: Dict[str, set[str]] = {
    "orders":       {"paid", "processing", "cancelled", "failed",
                     "pending", "shipped", "delivered", "refunded"},
    "payments":     {"captured", "failed", "pending", "refunded", "authorized"},
    "settlements":  {"settled", "pending", "failed", "processing"},
    "bank_transactions": {"credit", "debit", "cr", "dr"},
}

_VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP", "SGD", "AED"}

# Date formats tried in order
_DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d %b %Y",
    "%b %d %Y",
]


# ---------------------------------------------------------------------------
# Error model
# ---------------------------------------------------------------------------
@dataclass
class ValidationError:
    row: int        # 1-based (header = row 0)
    field: str
    message: str


@dataclass
class ValidationResult:
    dataset_type: str
    row_count: int
    valid_count: int
    error_count: int
    errors: List[ValidationError] = field(default_factory=list)
    valid_rows: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_amount(value: Any) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse an amount value into integer paise.

    Accepts:
      - integer 150000 → 150000 paise
      - float 1500.00  → 150000 paise (multiply × 100)
      - string "1,500.00" → 150000 paise
      - string "₹1500"   → 150000 paise

    Returns (paise_int, error_message).
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, "Missing amount value"

    raw = str(value).strip()
    # strip currency symbols and commas
    raw = re.sub(r"[₹$€£,\s]", "", raw)
    try:
        f = float(raw)
    except ValueError:
        return None, f"Cannot parse amount '{value}' as a number"

    if f < 0:
        return None, f"Amount must be non-negative (got {value})"

    # Decide paise vs rupees heuristic:
    # If the string had a decimal part (fractional component), treat as rupees
    if "." in raw or f != int(f):
        paise = round(f * 100)
    else:
        paise = int(f)

    return paise, None


def _parse_date(value: Any) -> Tuple[Optional[datetime], Optional[str]]:
    """Try a sequence of date formats; return (datetime, None) or (None, error)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, "Missing date value"

    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value).to_pydatetime(), None

    raw = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt), None
        except ValueError:
            continue

    # pandas last-resort parse
    try:
        return pd.to_datetime(raw, dayfirst=True).to_pydatetime(), None
    except Exception:
        return None, f"Cannot parse date '{value}'"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_csv(
    df: pd.DataFrame,
    dataset_type: str,
    column_mapping: Dict[str, str],
) -> ValidationResult:
    """
    Validate a DataFrame (already loaded from CSV) against *dataset_type* rules.

    Parameters
    ----------
    df             : raw DataFrame with original column names
    dataset_type   : one of the known types (orders, payments, …)
    column_mapping : {original_col → canonical_col} from mapper

    Returns
    -------
    ValidationResult with valid_rows (canonical column names, amount as paise).
    """
    errors: List[ValidationError] = []
    valid_rows: List[Dict[str, Any]] = []

    # ── 1. Rename to canonical names ────────────────────────────────────────
    df = df.rename(columns=column_mapping)

    required_cols = DATASET_REQUIRED.get(dataset_type, [])
    numeric_cols  = _NUMERIC_COLS.get(dataset_type, [])
    date_cols     = _DATE_COLS.get(dataset_type, [])
    required_dates = _DATE_REQUIRED.get(dataset_type, [])
    pk_col        = _PRIMARY_KEY.get(dataset_type)
    status_col    = _STATUS_COLS.get(dataset_type)
    valid_statuses = _VALID_STATUSES.get(dataset_type, set())

    # ── 2. Check all required columns are present ───────────────────────────
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        # File-level error — cannot validate rows
        return ValidationResult(
            dataset_type=dataset_type,
            row_count=len(df),
            valid_count=0,
            error_count=len(df),
            errors=[
                ValidationError(
                    row=0,
                    field=", ".join(missing_cols),
                    message=f"Required column(s) missing from file: {', '.join(missing_cols)}",
                )
            ],
        )

    # ── 3. Duplicate primary key scan (whole-file) ──────────────────────────
    dup_pk_set: set = set()
    if pk_col and pk_col in df.columns:
        counts = df[pk_col].value_counts()
        dup_pk_set = set(counts[counts > 1].index.astype(str))

    # ── 4. Row-level validation ─────────────────────────────────────────────
    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based, header = row 1
        row_errors: List[ValidationError] = []
        parsed_row: Dict[str, Any] = {}

        # copy all columns into parsed_row as strings first
        for col in df.columns:
            val = row.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                parsed_row[col] = None
            else:
                parsed_row[col] = val

        # (a) Null check on required columns
        for col in required_cols:
            if col not in df.columns:
                continue
            val = row.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
                row_errors.append(ValidationError(row_num, col, f"Missing required field '{col}'"))

        # (b) Duplicate primary key
        if pk_col and pk_col in df.columns:
            pk_val = str(row.get(pk_col, "")).strip()
            if pk_val in dup_pk_set:
                row_errors.append(ValidationError(
                    row_num, pk_col,
                    f"Duplicate {pk_col} '{pk_val}' — appears more than once in file",
                ))

        # (c) Numeric / amount columns
        for col in numeric_cols:
            if col not in df.columns:
                continue
            val = row.get(col)
            paise, err = _parse_amount(val)
            if err:
                row_errors.append(ValidationError(row_num, col, err))
            else:
                parsed_row[col] = paise   # overwrite with integer paise

        # (d) Date columns
        for col in date_cols:
            if col not in df.columns:
                continue
            val = row.get(col)
            is_required = col in required_dates
            if val is None or (isinstance(val, float) and pd.isna(val)):
                if is_required:
                    row_errors.append(ValidationError(row_num, col, f"Missing required date '{col}'"))
                else:
                    parsed_row[col] = None
                continue
            dt, err = _parse_date(val)
            if err:
                row_errors.append(ValidationError(row_num, col, err))
            else:
                parsed_row[col] = dt

        # (e) Status / direction enum check
        if status_col and status_col in df.columns:
            val = str(row.get(status_col, "")).strip()
            if val and valid_statuses and val.lower() not in valid_statuses:
                row_errors.append(ValidationError(
                    row_num, status_col,
                    f"Invalid {status_col} '{val}'. Expected one of: "
                    f"{', '.join(sorted(valid_statuses))}",
                ))
            elif status_col == "direction" and val:
                # normalise direction to CREDIT / DEBIT
                parsed_row[status_col] = "CREDIT" if val.lower() in {"credit", "cr"} else "DEBIT"

        # (f) Currency column
        if "currency" in df.columns:
            ccy = str(row.get("currency", "INR")).strip().upper()
            if ccy and ccy not in _VALID_CURRENCIES:
                row_errors.append(ValidationError(
                    row_num, "currency",
                    f"Invalid currency '{ccy}'. Expected one of: "
                    f"{', '.join(sorted(_VALID_CURRENCIES))}",
                ))
            else:
                parsed_row["currency"] = ccy if ccy else "INR"

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_rows.append(parsed_row)

    return ValidationResult(
        dataset_type=dataset_type,
        row_count=len(df),
        valid_count=len(valid_rows),
        error_count=len(df) - len(valid_rows),
        errors=errors,
        valid_rows=valid_rows,
    )
