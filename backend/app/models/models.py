"""
SQLAlchemy ORM models for all 7 Phase-1 database tables.

All monetary amounts are stored as BIGINT (paise / smallest currency unit)
to avoid floating-point rounding errors in financial calculations.

1 INR = 100 paise
e.g. ₹1,500.00 is stored as 150000 (paise)
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all models."""
    pass


# ---------------------------------------------------------------------------
# 1. ORDERS
# ---------------------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(String(100), nullable=True)
    order_amount = Column(BigInteger, nullable=False)   # paise
    currency = Column(String(10), default="INR", nullable=False)
    order_date = Column(DateTime, nullable=False)
    payment_mode = Column(String(50), nullable=True)
    order_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    payments = relationship("Payment", back_populates="order")

    __table_args__ = (
        Index("ix_orders_order_date", "order_date"),
        Index("ix_orders_order_status", "order_status"),
    )


# ---------------------------------------------------------------------------
# 2. PAYMENTS
# ---------------------------------------------------------------------------
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String(100), unique=True, nullable=False, index=True)
    order_id = Column(
        String(100),
        ForeignKey("orders.order_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(BigInteger, nullable=False)          # paise
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), nullable=False)          # captured, failed, pending
    payment_method = Column(String(50), nullable=True)   # card, upi, netbanking
    payment_captured_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="payments")
    settlement_lines = relationship("SettlementLine", back_populates="payment")

    __table_args__ = (
        Index("ix_payments_status", "status"),
        Index("ix_payments_payment_captured_at", "payment_captured_at"),
    )


# ---------------------------------------------------------------------------
# 3. SETTLEMENTS
# ---------------------------------------------------------------------------
class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(String(100), unique=True, nullable=False, index=True)
    settlement_date = Column(DateTime, nullable=False)
    gross_amount = Column(BigInteger, nullable=False)         # paise (sum of payments)
    fee_amount = Column(BigInteger, nullable=False)           # paise (platform fee)
    tax_amount = Column(BigInteger, nullable=False)           # paise (GST on fee)
    adjustment_amount = Column(BigInteger, default=0)         # paise (credits/debits)
    net_amount = Column(BigInteger, nullable=False)           # paise (gross - fee - tax + adj)
    settlement_utr = Column(String(100), unique=True, nullable=True, index=True)
    status = Column(String(50), nullable=False)               # settled, pending, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    settlement_lines = relationship("SettlementLine", back_populates="settlement")

    __table_args__ = (
        Index("ix_settlements_settlement_date", "settlement_date"),
        Index("ix_settlements_status", "status"),
    )


# ---------------------------------------------------------------------------
# 4. SETTLEMENT LINES
# ---------------------------------------------------------------------------
class SettlementLine(Base):
    __tablename__ = "settlement_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(
        String(100),
        ForeignKey("settlements.settlement_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id = Column(
        String(100),
        ForeignKey("payments.payment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(BigInteger, nullable=False)      # paise (gross)
    fee = Column(BigInteger, nullable=False)         # paise (platform fee)
    tax = Column(BigInteger, nullable=False)         # paise (GST on fee)
    net_amount = Column(BigInteger, nullable=False)  # paise (amount - fee - tax)

    # Relationships
    settlement = relationship("Settlement", back_populates="settlement_lines")
    payment = relationship("Payment", back_populates="settlement_lines")


# ---------------------------------------------------------------------------
# 5. BANK TRANSACTIONS
# ---------------------------------------------------------------------------
class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_entry_id = Column(String(100), unique=True, nullable=False, index=True)
    bank_date = Column(DateTime, nullable=False)
    amount = Column(BigInteger, nullable=False)        # paise
    direction = Column(String(10), nullable=False)     # CREDIT | DEBIT
    narration = Column(Text, nullable=True)
    utr = Column(String(100), nullable=True, index=True)
    transaction_type = Column(String(50), nullable=True)  # SETTLEMENT | FEE | OTHER
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_bank_transactions_bank_date", "bank_date"),
        Index("ix_bank_transactions_direction", "direction"),
    )


# ---------------------------------------------------------------------------
# 6. RECONCILIATION RESULTS
# ---------------------------------------------------------------------------
class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(100), nullable=False)      # ORDER | PAYMENT | SETTLEMENT
    entity_id = Column(String(100), nullable=False, index=True)
    related_entity_id = Column(String(100), nullable=True)
    match_type = Column(String(100), nullable=True)
    status = Column(String(100), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=True)
    expected_amount = Column(BigInteger, nullable=True)    # paise
    actual_amount = Column(BigInteger, nullable=True)      # paise
    difference = Column(BigInteger, nullable=True)         # paise (actual - expected)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_reconciliation_entity_type", "entity_type"),
        Index("ix_reconciliation_status", "status"),
    )


# ---------------------------------------------------------------------------
# 7. DATA IMPORTS (audit log)
# ---------------------------------------------------------------------------
class DataImport(Base):
    __tablename__ = "data_imports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    dataset_type = Column(String(100), nullable=False)  # orders | payments | settlements | ...
    row_count = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)         # success | failed | partial
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 8. REFUNDS  (Phase 2A — source data)
# ---------------------------------------------------------------------------
class Refund(Base):
    """
    Payment gateway refund records.
    Links a refund back to the original payment, order, and settlement.
    Amount stored as paise (BigInteger).
    """
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    refund_id = Column(String(100), unique=True, nullable=False, index=True)
    payment_id = Column(String(100), nullable=False, index=True)
    order_id = Column(String(100), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)            # paise
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), nullable=False)            # processed | pending | failed
    refund_date = Column(DateTime, nullable=True)
    settlement_id = Column(String(100), nullable=True, index=True)  # which settlement carried this refund
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_refunds_status", "status"),
    )


# ---------------------------------------------------------------------------
# 9. LEDGER ENTRIES  (Phase 2A — accounting source data)
# ---------------------------------------------------------------------------
class LedgerEntry(Base):
    """
    Accounting general ledger entries used for tax-line matching.
    Each entry corresponds to a specific financial event:
    REVENUE | FEE_EXPENSE | TAX | REFUND | BANK_CREDIT
    Amount stored as paise (BigInteger).
    """
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(100), unique=True, nullable=False, index=True)
    entry_type = Column(String(50), nullable=False)        # REVENUE | FEE_EXPENSE | TAX | REFUND | BANK_CREDIT
    reference_id = Column(String(100), nullable=True, index=True)  # settlement_id / refund_id / order_id
    amount = Column(BigInteger, nullable=False)            # paise
    currency = Column(String(10), default="INR", nullable=False)
    entry_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ledger_entries_entry_type", "entry_type"),
    )


# ---------------------------------------------------------------------------
# 10. SETTLEMENT CALCULATIONS  (Phase 2A — computed results)
# ---------------------------------------------------------------------------
class SettlementCalculation(Base):
    """
    Deterministic fee/tax/net calculation result for each settlement.

    Formula:
      expected_net_amount =
        gross_amount
        - fee_amount       (payment gateway fee)
        - tax_amount       (GST 18% on fee)
        - refund_adjustment  (customer refunds deducted)
        + other_adjustment   (positive adjustments e.g. clawback reversals)

    calculation_status:
      CORRECT       — expected_net matches reported_net within tolerance
      DISCREPANCY   — expected_net differs from reported_net
      UNVERIFIABLE  — insufficient data to calculate

    All amounts in paise (BigInteger).
    """
    __tablename__ = "settlement_calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(String(100), unique=True, nullable=False, index=True)
    gross_amount = Column(BigInteger, nullable=False)           # sum of payment amounts in batch
    fee_amount = Column(BigInteger, nullable=False)             # gateway fee
    tax_amount = Column(BigInteger, nullable=False)             # GST on fee
    refund_adjustment = Column(BigInteger, default=0)           # total refunds deducted
    other_adjustment = Column(BigInteger, default=0)            # other credits/debits
    expected_net_amount = Column(BigInteger, nullable=False)    # calculated from formula above
    reported_net_amount = Column(BigInteger, nullable=False)    # as stored in settlements table
    calculation_status = Column(String(50), nullable=False)     # CORRECT | DISCREPANCY | UNVERIFIABLE
    calculation_difference = Column(BigInteger, default=0)      # reported - expected (paise)
    payment_count = Column(Integer, default=0)                  # number of payments in batch
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_settlement_calc_status", "calculation_status"),
    )


# ---------------------------------------------------------------------------
# 11. TAX RECONCILIATION RESULTS  (Phase 2A — validation results)
# ---------------------------------------------------------------------------
class TaxReconciliationResult(Base):
    """
    Per-settlement, per-component tax-line validation against accounting ledger.

    For each settlement, validates each financial component:
      - GROSS : sum of gross payments
      - FEE   : gateway fee charged
      - TAX   : GST on fee (18%)
      - REFUND: total refund adjustments
      - NET   : final bank credit amount

    status values:
      MATCHED              — settlement component matches ledger entry exactly
      MISSING_LEDGER_ENTRY — component present in settlement but not in ledger
      AMOUNT_MISMATCH      — component present in both but amounts differ
      DUPLICATE_ENTRY      — multiple ledger entries for same component
      PENDING_REVIEW       — cannot determine without human review

    All amounts in paise (BigInteger).
    """
    __tablename__ = "tax_reconciliation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(String(100), nullable=False, index=True)
    component = Column(String(50), nullable=False)          # GROSS | FEE | TAX | REFUND | NET
    expected_amount = Column(BigInteger, nullable=True)     # from settlement record (paise)
    ledger_amount = Column(BigInteger, nullable=True)       # from ledger_entries (paise)
    difference = Column(BigInteger, nullable=True)          # ledger - expected (paise)
    status = Column(String(50), nullable=False)             # see docstring above
    ledger_entry_id = Column(String(100), nullable=True)    # matching ledger entry if found
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tax_recon_status", "status"),
        Index("ix_tax_recon_component", "component"),
    )


# ---------------------------------------------------------------------------
# 12. REFUND RECONCILIATION RESULTS  (Phase 2A — refund matching results)
# ---------------------------------------------------------------------------
class RefundReconciliationResult(Base):
    """
    Per-refund reconciliation result across payment gateway → settlement → ledger.

    Traces each refund through:
      1. Payment gateway refund record (source of truth for refund_amount)
      2. Settlement adjustment (was refund deducted from payout?)
      3. Accounting ledger entry (was refund recorded in books?)

    status values:
      REFUND_MATCHED                    — all three layers consistent
      REFUND_MISSING_IN_LEDGER          — refund in gateway but no ledger entry
      REFUND_AMOUNT_MISMATCH            — amounts differ between gateway and ledger
      DUPLICATE_REFUND                  — same refund appears multiple times in ledger
      REFUND_PENDING                    — refund not yet processed
      REFUND_SETTLEMENT_ADJUSTMENT_MISSING — refund not reflected in settlement

    All amounts in paise (BigInteger).
    """
    __tablename__ = "refund_reconciliation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    refund_id = Column(String(100), nullable=False, index=True)
    payment_id = Column(String(100), nullable=True, index=True)
    order_id = Column(String(100), nullable=True)
    settlement_id = Column(String(100), nullable=True)
    ledger_entry_id = Column(String(100), nullable=True)    # matched ledger entry if found
    refund_amount = Column(BigInteger, nullable=False)       # from gateway (paise)
    ledger_amount = Column(BigInteger, nullable=True)        # from ledger (paise) — None if missing
    amount_difference = Column(BigInteger, nullable=True)    # ledger - gateway (paise)
    refund_status = Column(String(80), nullable=False)       # see docstring above
    duplicate_count = Column(Integer, default=0)            # how many duplicate ledger entries found
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_refund_recon_status", "refund_status"),
    )


# ---------------------------------------------------------------------------
# 13. SHIPMENTS  (Phase 2B — fulfillment data)
# ---------------------------------------------------------------------------
class Shipment(Base):
    """
    Logistics and fulfillment tracking records for customer orders.
    Used by the Paid-but-unfulfilled alert engine to detect captured payments
    without fulfillment confirmation.
    """
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(100), unique=True, nullable=False, index=True)
    order_id = Column(String(100), nullable=False, index=True)
    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)           # Bluedart | Delhivery | Ekart | FedEx
    status = Column(String(50), nullable=False)            # DELIVERED | IN_TRANSIT | SHIPPED | PENDING
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_shipments_status", "status"),
    )


# ---------------------------------------------------------------------------
# 14. FINANCIAL EXCEPTIONS  (Phase 2B — investigation cases)
# ---------------------------------------------------------------------------
class FinancialException(Base):
    """
    Central financial exception repository for investigation and resolution.
    Captures anomalies detected across:
      - PAID_BUT_UNFULFILLED (captured payment missing shipment after threshold)
      - SETTLEMENT_MISSING_IN_BANK (settlement past bank credit window without match)
      - RECONCILIATION_MISMATCH (order/payment amount discrepancy)
      - CALCULATION_DISCREPANCY (fee/tax/net settlement calculation variance)
      - REFUND_MISSING_IN_LEDGER (refund in gateway not posted to books)

    Risk levels: CRITICAL | HIGH | MEDIUM | LOW
    Statuses: OPEN | ASSIGNED | IN_REVIEW | RESOLVED | DISMISSED | ESCALATED
    Suggested owners: Finance | Operations | Support
    """
    __tablename__ = "financial_exceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(100), unique=True, nullable=False, index=True)
    exception_type = Column(String(100), nullable=False, index=True)
    risk_level = Column(String(50), nullable=False, index=True)  # CRITICAL | HIGH | MEDIUM | LOW
    value_at_risk = Column(BigInteger, nullable=False)           # paise
    status = Column(String(50), nullable=False, default="OPEN", index=True)
    suggested_owner = Column(String(50), nullable=False, index=True)  # Finance | Operations | Support
    related_order_id = Column(String(100), nullable=True, index=True)
    related_payment_id = Column(String(100), nullable=True, index=True)
    related_settlement_id = Column(String(100), nullable=True, index=True)
    related_bank_entry_id = Column(String(100), nullable=True, index=True)
    evidence = Column(JSON, nullable=True)                      # structured audit trail & linked records
    explanation = Column(Text, nullable=False)                  # verified deterministic explanation
    triggering_rule = Column(Text, nullable=False)              # exact rule logic that generated alert
    detected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assignee = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_fin_exc_detected_at", "detected_at"),
    )


# ---------------------------------------------------------------------------
# 15. SETTLEMENT FORECASTS  (Phase 4 — forward projection engine)
# ---------------------------------------------------------------------------
class SettlementForecast(Base):
    """
    Forward settlement projections for captured payments not yet settled.

    For each un-settled payment, the forecast engine creates one record per
    horizon (1, 3, 7, 14 days) projecting when the payment should reach bank.

    Basis values:
      HISTORICAL_AVERAGE    — derived from average gateway settlement lag in DB
      GATEWAY_SCHEDULE      — fixed per-gateway expected lag (Razorpay: 2d, PayU: 3d, Stripe: 5d)
      PAYMENT_CAPTURE_DATE  — fallback using capture timestamp + default 3-day lag

    Status values:
      PENDING   — payment captured but not yet settled
      SETTLED   — matching settlement/bank credit confirmed
      OVERDUE   — expected_settlement_date passed without settlement
      CANCELLED — payment refunded / voided

    IMPORTANT: These are EXPECTED projections only.
    They must NEVER be combined with actual bank credits.
    All amounts stored as paise (BigInteger).
    """
    __tablename__ = "settlement_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_id = Column(String(100), unique=True, nullable=False, index=True)
    payment_id = Column(String(100), nullable=False, index=True)
    order_id = Column(String(100), nullable=True, index=True)
    settlement_id = Column(String(100), nullable=True, index=True)   # set when settled
    expected_amount_paise = Column(BigInteger, nullable=False)        # paise
    horizon_days = Column(Integer, nullable=False)                    # 1 | 3 | 7 | 14
    expected_settlement_date = Column(DateTime, nullable=False)
    basis = Column(String(50), nullable=False)                        # see docstring
    status = Column(String(50), nullable=False, default="PENDING")   # PENDING | SETTLED | OVERDUE | CANCELLED
    payment_captured_at = Column(DateTime, nullable=True)
    gateway = Column(String(100), nullable=True)                      # Razorpay | PayU | Stripe | ...
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_sf_status", "status"),
        Index("ix_sf_horizon", "horizon_days"),
        Index("ix_sf_expected_date", "expected_settlement_date"),
    )


# ---------------------------------------------------------------------------
# 16. CASH GAP ALERTS  (Phase 4 — gap detection)
# ---------------------------------------------------------------------------
class CashGapAlert(Base):
    """
    Alerts for payments that are delayed or overdue for settlement.

    Alert types:
      SETTLEMENT_DELAY   — payment captured, settlement expected but no bank credit yet
      RISK_GAP           — settlement issued but no bank match within 48h window
      OVERDUE_SETTLEMENT — forecast overdue (past expected date) without settlement

    Severity:
      CRITICAL — gap > 7 days
      HIGH     — gap 4-7 days
      MEDIUM   — gap 2-3 days
      LOW      — gap 1 day

    Status:
      OPEN         — newly detected, no action taken
      ACKNOWLEDGED — team aware, monitoring
      RESOLVED     — gap closed (settlement/bank credit received)

    All amounts stored as paise (BigInteger).
    """
    __tablename__ = "cash_gap_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)      # SETTLEMENT_DELAY | RISK_GAP | OVERDUE_SETTLEMENT
    payment_id = Column(String(100), nullable=True, index=True)
    settlement_id = Column(String(100), nullable=True, index=True)
    order_id = Column(String(100), nullable=True, index=True)
    expected_date = Column(DateTime, nullable=True)
    actual_date = Column(DateTime, nullable=True)                     # set when resolved
    gap_days = Column(Integer, nullable=False, default=0)
    gap_amount_paise = Column(BigInteger, nullable=False)             # paise
    severity = Column(String(50), nullable=False, index=True)        # CRITICAL | HIGH | MEDIUM | LOW
    status = Column(String(50), nullable=False, default="OPEN", index=True)  # OPEN | ACKNOWLEDGED | RESOLVED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_cga_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# 17. AUDIT TRAIL EVENTS  (Phase 4 — immutable event log)
# ---------------------------------------------------------------------------
class AuditTrailEvent(Base):
    """
    Immutable chronological log of all state changes in CashPilot AI.

    IMPORTANT:
      - Records must NEVER be deleted or updated.
      - created_at is set once at insert time and is immutable.
      - This is the authoritative history for compliance and audit purposes.

    Entity types:
      EXCEPTION_CASE  — FinancialException case
      CASH_GAP_ALERT  — CashGapAlert record
      FORECAST        — SettlementForecast record
      SYSTEM          — system-level events (detection runs, reconciliation)

    Event types:
      DETECTION        — first detection / creation of entity
      STATUS_CHANGE    — status field changed (e.g. OPEN → IN_REVIEW)
      ASSIGNMENT       — assignee field changed
      NOTE_ADDED       — resolution_notes updated
      ACKNOWLEDGEMENT  — alert acknowledged
      RESOLUTION       — entity moved to RESOLVED/DISMISSED
      ESCALATION       — entity moved to ESCALATED
      ENGINE_RUN       — a detection or forecast engine was triggered
    """
    __tablename__ = "audit_trail_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)     # EXCEPTION_CASE | CASH_GAP_ALERT | FORECAST | SYSTEM
    entity_id = Column(String(100), nullable=False, index=True)      # case_id / alert_id / forecast_id / "SYSTEM"
    event_type = Column(String(50), nullable=False, index=True)      # see docstring
    actor = Column(String(100), nullable=False, default="system")    # user | system
    from_value = Column(JSON, nullable=True)                         # previous state (for STATUS_CHANGE)
    to_value = Column(JSON, nullable=True)                           # new state
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)           # IMMUTABLE — never update

    __table_args__ = (
        Index("ix_ate_created_at", "created_at"),
    )


