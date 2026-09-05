"""
Database importer — commits validated rows into PostgreSQL.

Reads valid_rows from an upload session and bulk-inserts them into the
appropriate table.  Duplicate primary keys are skipped (ON CONFLICT DO NOTHING
equivalent via SQLAlchemy).

All monetary amounts must already be in integer paise before reaching this module.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    BankTransaction,
    DataImport,
    Order,
    Payment,
    Settlement,
    SettlementLine,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    imported: int
    skipped: int
    dataset_type: str
    data_import_id: int
    message: str


# ---------------------------------------------------------------------------
# Dataset-specific row → ORM object converters
# ---------------------------------------------------------------------------
def _to_order(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_id":     str(row["order_id"]).strip(),
        "customer_id":  _s(row, "customer_id"),
        "order_amount": int(row["order_amount"]),
        "currency":     str(row.get("currency", "INR")).upper(),
        "order_date":   row["order_date"],
        "payment_mode": _s(row, "payment_mode"),
        "order_status": str(row.get("order_status", "unknown")).lower(),
        "created_at":   datetime.utcnow(),
    }


def _to_payment(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "payment_id":          str(row["payment_id"]).strip(),
        "order_id":            _s(row, "order_id"),
        "amount":              int(row["amount"]),
        "currency":            str(row.get("currency", "INR")).upper(),
        "status":              str(row.get("status", "unknown")).lower(),
        "payment_method":      _s(row, "payment_method"),
        "payment_captured_at": row.get("payment_captured_at"),
        "created_at":          datetime.utcnow(),
    }


def _to_settlement(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "settlement_id":    str(row["settlement_id"]).strip(),
        "settlement_date":  row["settlement_date"],
        "gross_amount":     int(row["gross_amount"]),
        "fee_amount":       int(row["fee_amount"]),
        "tax_amount":       int(row["tax_amount"]),
        "adjustment_amount": int(row.get("adjustment_amount") or 0),
        "net_amount":       int(row["net_amount"]),
        "settlement_utr":   _s(row, "settlement_utr"),
        "status":           str(row.get("status", "settled")).lower(),
        "created_at":       datetime.utcnow(),
    }


def _to_settlement_line(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "settlement_id": str(row["settlement_id"]).strip(),
        "payment_id":    str(row["payment_id"]).strip(),
        "amount":        int(row["amount"]),
        "fee":           int(row["fee"]),
        "tax":           int(row["tax"]),
        "net_amount":    int(row["net_amount"]),
    }


def _to_bank_transaction(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "bank_entry_id":    str(row["bank_entry_id"]).strip(),
        "bank_date":        row["bank_date"],
        "amount":           int(row["amount"]),
        "direction":        str(row.get("direction", "CREDIT")).upper(),
        "narration":        _s(row, "narration"),
        "utr":              _s(row, "utr"),
        "transaction_type": _s(row, "transaction_type"),
        "created_at":       datetime.utcnow(),
    }


def _s(row: Dict[str, Any], key: str) -> Optional[str]:
    val = row.get(key)
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return None
    s = str(val).strip()
    return s if s else None


# ---------------------------------------------------------------------------
# Dataset → (table_model, converter, pk_column)
# ---------------------------------------------------------------------------
_HANDLERS = {
    "orders":            (Order,           _to_order,            "order_id"),
    "payments":          (Payment,         _to_payment,          "payment_id"),
    "settlements":       (Settlement,      _to_settlement,       "settlement_id"),
    "settlement_lines":  (SettlementLine,  _to_settlement_line,  None),
    "bank_transactions": (BankTransaction, _to_bank_transaction, "bank_entry_id"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def commit_rows(
    db: Session,
    dataset_type: str,
    valid_rows: List[Dict[str, Any]],
    filename: str,
) -> ImportResult:
    """
    Insert *valid_rows* into the appropriate table.

    - Duplicate primary keys are silently skipped.
    - A DataImport audit record is created.
    """
    handler = _HANDLERS.get(dataset_type)
    if not handler:
        raise ValueError(f"Unknown dataset_type '{dataset_type}'")

    model_cls, converter, pk_col = handler

    imported = 0
    skipped = 0

    for row in valid_rows:
        try:
            record = converter(row)
            db_obj = model_cls(**record)
            db.add(db_obj)
            db.flush()  # catch constraint errors per-row
            imported += 1
        except IntegrityError:
            db.rollback()
            skipped += 1
            logger.debug("Skipped duplicate row (PK conflict): %s", row.get(pk_col or ""))
        except Exception as exc:
            db.rollback()
            skipped += 1
            logger.warning("Skipped row due to error: %s — %s", exc, row)

    db.commit()

    # ── Create audit record ──────────────────────────────────────────────────
    audit = DataImport(
        filename=filename,
        dataset_type=dataset_type,
        row_count=imported + skipped,
        status="success" if skipped == 0 else "partial",
        error_count=skipped,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    return ImportResult(
        imported=imported,
        skipped=skipped,
        dataset_type=dataset_type,
        data_import_id=audit.id,
        message=(
            f"Imported {imported} records into '{dataset_type}'."
            + (f" {skipped} duplicates skipped." if skipped else "")
        ),
    )
