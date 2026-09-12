"""
Demo data CSV loader service.

Reads the CSV files from data/demo/ and loads them into the database.
All monetary amounts in CSVs are stored as BIGINT paise (no conversion needed).

Load order (respects foreign key dependencies):
  1. orders
  2. payments          (FK → orders)
  3. settlements
  4. settlement_lines  (FK → settlements, payments)
  5. bank_transactions

Clear order (reverse of load):
  settlement_lines → payments → settlements → orders → bank_transactions
"""

import os
from datetime import datetime
from typing import Dict

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import (
    BankTransaction,
    DataImport,
    Order,
    Payment,
    ReconciliationResult,
    Settlement,
    SettlementLine,
    Refund,
    LedgerEntry,
    SettlementCalculation,
    TaxReconciliationResult,
    RefundReconciliationResult,
    Shipment,
    FinancialException,
    CashGapAlert,
    SettlementForecast,
)

# Resolve data directory relative to this file
# loader.py lives at: backend/app/services/data_ingestion/loader.py
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data", "demo")


def _csv_path(filename: str) -> str:
    """Resolve demo CSV filename across local backend and monorepo root paths."""
    candidates = [
        os.path.join(_BACKEND_ROOT, "data", "demo", filename),
        os.path.join(DATA_DIR, filename),
        os.path.join(os.getcwd(), "data", "demo", filename),
        os.path.join(os.getcwd(), "..", "data", "demo", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Could not locate '{filename}' in any candidate paths: {candidates}")



def _parse_dt(value: str) -> datetime:
    """Parse a datetime string from CSV."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def _clear_all_data(db: Session) -> None:
    """Delete all data in safe reverse-dependency order (Phase 1 + Phase 2A + Phase 4)."""
    # Phase 4 forward forecast & gap tables
    db.query(CashGapAlert).delete(synchronize_session=False)
    db.query(SettlementForecast).delete(synchronize_session=False)
    # Phase 2B investigation tables
    db.query(FinancialException).delete(synchronize_session=False)
    db.query(Shipment).delete(synchronize_session=False)
    # Phase 2A result tables first (no FK deps on them)
    db.query(RefundReconciliationResult).delete(synchronize_session=False)
    db.query(TaxReconciliationResult).delete(synchronize_session=False)
    db.query(SettlementCalculation).delete(synchronize_session=False)
    # Phase 2A source tables
    db.query(Refund).delete(synchronize_session=False)
    db.query(LedgerEntry).delete(synchronize_session=False)
    # Phase 1 tables
    db.query(ReconciliationResult).delete(synchronize_session=False)
    db.query(SettlementLine).delete(synchronize_session=False)
    db.query(Settlement).delete(synchronize_session=False)
    db.query(Payment).delete(synchronize_session=False)
    db.query(Order).delete(synchronize_session=False)
    db.query(BankTransaction).delete(synchronize_session=False)
    db.query(DataImport).delete(synchronize_session=False)
    db.commit()


def _log_import(db: Session, filename: str, dataset_type: str, row_count: int) -> None:
    record = DataImport(
        filename=filename,
        dataset_type=dataset_type,
        row_count=row_count,
        status="success",
        error_count=0,
        created_at=datetime.utcnow(),
    )
    db.add(record)


def load_demo_data(db: Session) -> Dict[str, int]:
    """
    Load all demo CSVs into the database.
    Returns a dict of {table_name: row_count}.
    """
    # ------------------------------------------------------------------
    # Step 0: Clear existing data
    # ------------------------------------------------------------------
    _clear_all_data(db)

    counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Step 1: Orders
    # ------------------------------------------------------------------
    orders_df = pd.read_csv(_csv_path("orders.csv"))
    orders_objects = []
    for _, row in orders_df.iterrows():
        orders_objects.append(
            Order(
                order_id=str(row["order_id"]),
                customer_id=str(row["customer_id"]) if pd.notna(row.get("customer_id")) else None,
                order_amount=int(row["order_amount"]),
                currency=str(row.get("currency", "INR")),
                order_date=_parse_dt(row["order_date"]),
                payment_mode=str(row["payment_mode"]) if pd.notna(row.get("payment_mode")) else None,
                order_status=str(row["order_status"]),
                created_at=_parse_dt(row["created_at"]) if pd.notna(row.get("created_at")) else datetime.utcnow(),
            )
        )
    db.bulk_save_objects(orders_objects)
    db.commit()
    counts["orders"] = len(orders_objects)
    _log_import(db, "orders.csv", "orders", len(orders_objects))

    # ------------------------------------------------------------------
    # Step 2: Payments
    # ------------------------------------------------------------------
    payments_df = pd.read_csv(_csv_path("payments.csv"))
    payment_objects = []
    for _, row in payments_df.iterrows():
        payment_objects.append(
            Payment(
                payment_id=str(row["payment_id"]),
                order_id=str(row["order_id"]) if pd.notna(row.get("order_id")) else None,
                amount=int(row["amount"]),
                currency=str(row.get("currency", "INR")),
                status=str(row["status"]),
                payment_method=str(row["payment_method"]) if pd.notna(row.get("payment_method")) else None,
                payment_captured_at=_parse_dt(row["payment_captured_at"]) if pd.notna(row.get("payment_captured_at")) else None,
                created_at=_parse_dt(row["created_at"]) if pd.notna(row.get("created_at")) else datetime.utcnow(),
            )
        )
    db.bulk_save_objects(payment_objects)
    db.commit()
    counts["payments"] = len(payment_objects)
    _log_import(db, "payments.csv", "payments", len(payment_objects))

    # ------------------------------------------------------------------
    # Step 3: Settlements
    # ------------------------------------------------------------------
    settlements_df = pd.read_csv(_csv_path("settlements.csv"))
    settlement_objects = []
    for _, row in settlements_df.iterrows():
        settlement_objects.append(
            Settlement(
                settlement_id=str(row["settlement_id"]),
                settlement_date=_parse_dt(row["settlement_date"]),
                gross_amount=int(row["gross_amount"]),
                fee_amount=int(row["fee_amount"]),
                tax_amount=int(row["tax_amount"]),
                adjustment_amount=int(row.get("adjustment_amount", 0)) if pd.notna(row.get("adjustment_amount")) else 0,
                net_amount=int(row["net_amount"]),
                settlement_utr=str(row["settlement_utr"]) if pd.notna(row.get("settlement_utr")) else None,
                status=str(row["status"]),
                created_at=_parse_dt(row["created_at"]) if pd.notna(row.get("created_at")) else datetime.utcnow(),
            )
        )
    db.bulk_save_objects(settlement_objects)
    db.commit()
    counts["settlements"] = len(settlement_objects)
    _log_import(db, "settlements.csv", "settlements", len(settlement_objects))

    # ------------------------------------------------------------------
    # Step 4: Settlement Lines
    # ------------------------------------------------------------------
    lines_df = pd.read_csv(_csv_path("settlement_lines.csv"))
    line_objects = []
    for _, row in lines_df.iterrows():
        line_objects.append(
            SettlementLine(
                settlement_id=str(row["settlement_id"]),
                payment_id=str(row["payment_id"]),
                amount=int(row["amount"]),
                fee=int(row["fee"]),
                tax=int(row["tax"]),
                net_amount=int(row["net_amount"]),
            )
        )
    db.bulk_save_objects(line_objects)
    db.commit()
    counts["settlement_lines"] = len(line_objects)
    _log_import(db, "settlement_lines.csv", "settlement_lines", len(line_objects))

    # ------------------------------------------------------------------
    # Step 5: Bank Transactions
    # ------------------------------------------------------------------
    bank_df = pd.read_csv(_csv_path("bank_statement.csv"))
    bank_objects = []
    for _, row in bank_df.iterrows():
        bank_objects.append(
            BankTransaction(
                bank_entry_id=str(row["bank_entry_id"]),
                bank_date=_parse_dt(row["bank_date"]),
                amount=int(row["amount"]),
                direction=str(row["direction"]),
                narration=str(row["narration"]) if pd.notna(row.get("narration")) else None,
                utr=str(row["utr"]) if pd.notna(row.get("utr")) else None,
                transaction_type=str(row["transaction_type"]) if pd.notna(row.get("transaction_type")) else None,
                created_at=_parse_dt(row["created_at"]) if pd.notna(row.get("created_at")) else datetime.utcnow(),
            )
        )
    db.bulk_save_objects(bank_objects)
    db.commit()
    counts["bank_transactions"] = len(bank_objects)
    _log_import(db, "bank_statement.csv", "bank_transactions", len(bank_objects))

    # ------------------------------------------------------------------
    # Step 6: Refunds (Phase 2A)
    # ------------------------------------------------------------------
    try:
        refunds_df = pd.read_csv(_csv_path("refunds.csv"))
        refund_objects = []
        for _, row in refunds_df.iterrows():
            refund_objects.append(
                Refund(
                    refund_id=str(row["refund_id"]),
                    payment_id=str(row["payment_id"]),
                    order_id=str(row["order_id"]) if pd.notna(row.get("order_id")) else None,
                    amount=int(row["amount"]),
                    currency=str(row.get("currency", "INR")),
                    status=str(row["status"]),
                    refund_date=_parse_dt(row["refund_date"]) if pd.notna(row.get("refund_date")) else None,
                    settlement_id=str(row["settlement_id"]) if pd.notna(row.get("settlement_id")) and str(row.get("settlement_id", "")).strip() else None,
                    reason=str(row["reason"]) if pd.notna(row.get("reason")) else None,
                    created_at=datetime.utcnow(),
                )
            )
        db.bulk_save_objects(refund_objects)
        db.commit()
        counts["refunds"] = len(refund_objects)
        _log_import(db, "refunds.csv", "refunds", len(refund_objects))
    except FileNotFoundError:
        counts["refunds"] = 0  # optional Phase 2A file

    # ------------------------------------------------------------------
    # Step 7: Ledger Entries (Phase 2A)
    # ------------------------------------------------------------------
    try:
        ledger_df = pd.read_csv(_csv_path("ledger_entries.csv"))
        ledger_objects = []
        for _, row in ledger_df.iterrows():
            ledger_objects.append(
                LedgerEntry(
                    entry_id=str(row["entry_id"]),
                    entry_type=str(row["entry_type"]),
                    reference_id=str(row["reference_id"]) if pd.notna(row.get("reference_id")) else None,
                    amount=int(row["amount"]),
                    currency=str(row.get("currency", "INR")),
                    entry_date=_parse_dt(row["entry_date"]) if pd.notna(row.get("entry_date")) else None,
                    description=str(row["description"]) if pd.notna(row.get("description")) else None,
                    created_at=datetime.utcnow(),
                )
            )
        db.bulk_save_objects(ledger_objects)
        db.commit()
        counts["ledger_entries"] = len(ledger_objects)
        _log_import(db, "ledger_entries.csv", "ledger_entries", len(ledger_objects))
    except FileNotFoundError:
        counts["ledger_entries"] = 0  # optional Phase 2A file

    # ------------------------------------------------------------------
    # Step 8: Shipments (Phase 2B)
    # ------------------------------------------------------------------
    try:
        shipments_df = pd.read_csv(_csv_path("shipments.csv"))
        shipment_objects = []
        for _, row in shipments_df.iterrows():
            shipment_objects.append(
                Shipment(
                    shipment_id=str(row["shipment_id"]),
                    order_id=str(row["order_id"]),
                    carrier=str(row["carrier"]) if pd.notna(row.get("carrier")) else None,
                    tracking_number=str(row["tracking_number"]) if pd.notna(row.get("tracking_number")) else None,
                    status=str(row["status"]),
                    shipped_at=_parse_dt(row["shipped_at"]) if pd.notna(row.get("shipped_at")) and str(row.get("shipped_at", "")).strip() else None,
                    delivered_at=_parse_dt(row["delivered_at"]) if pd.notna(row.get("delivered_at")) and str(row.get("delivered_at", "")).strip() else None,
                    created_at=_parse_dt(row["created_at"]) if pd.notna(row.get("created_at")) and str(row.get("created_at", "")).strip() else datetime.utcnow(),
                )
            )
        db.bulk_save_objects(shipment_objects)
        db.commit()
        counts["shipments"] = len(shipment_objects)
        _log_import(db, "shipments.csv", "shipments", len(shipment_objects))
    except FileNotFoundError:
        counts["shipments"] = 0  # optional Phase 2B file

    db.commit()
    return counts
