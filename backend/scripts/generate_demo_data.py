#!/usr/bin/env python3
"""
CASHpilot AI — Synthetic Demo Data Generator
=============================================
Generates a coherent demo merchant dataset for CashPilot AI Phase 1.

All monetary amounts are stored in PAISE (1 INR = 100 paise) as integers.

Generated files:
  data/demo/orders.csv
  data/demo/payments.csv
  data/demo/settlements.csv
  data/demo/settlement_lines.csv
  data/demo/bank_statement.csv
  data/ground_truth/ground_truth.csv

Run from the project root:
  python backend/scripts/generate_demo_data.py
"""

import csv
import os
import random
import string
from datetime import datetime, timedelta

# ─── Reproducible seed ────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

# ─── Output directories ───────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DEMO_DIR = os.path.join(PROJECT_ROOT, "data", "demo")
GT_DIR = os.path.join(PROJECT_ROOT, "data", "ground_truth")

os.makedirs(DEMO_DIR, exist_ok=True)
os.makedirs(GT_DIR, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def rnd_alphanum(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def rnd_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta), hours=random.randint(0, 23), minutes=random.randint(0, 59))

def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def calc_fee(amount_paise: int) -> int:
    """Platform fee: 2% of amount, integer paise."""
    return int(amount_paise * 2 / 100)

def calc_tax(fee_paise: int) -> int:
    """GST: 18% of fee, integer paise."""
    return int(fee_paise * 18 / 100)

# ─── Date window ──────────────────────────────────────────────────────────────
START = datetime(2024, 1, 1)
END   = datetime(2024, 12, 20)

# ─── Reference data ───────────────────────────────────────────────────────────
NUM_CUSTOMERS = 280
CUSTOMER_IDS = [f"CUST-{str(i).zfill(4)}" for i in range(1001, 1001 + NUM_CUSTOMERS)]

PRODUCTS = [
    # (category, name, price_min_paise, price_max_paise)
    ("Electronics", "Bluetooth Headphones",       299900,  1499900),
    ("Electronics", "Wireless Charger",             99900,   499900),
    ("Electronics", "USB-C Hub",                    149900,  599900),
    ("Electronics", "Smartwatch",                   499900,  2999900),
    ("Electronics", "Action Camera",               1499900,  4999900),
    ("Clothing",    "Cotton Kurta",                  49900,   299900),
    ("Clothing",    "Denim Jeans",                   79900,   499900),
    ("Clothing",    "Running Shoes",                149900,   799900),
    ("Clothing",    "Casual T-Shirt",                29900,   149900),
    ("Clothing",    "Winter Jacket",                299900,  1499900),
    ("Home",        "Stainless Steel Water Bottle",  39900,   149900),
    ("Home",        "Air Purifier",                 499900,  2499900),
    ("Home",        "Bed Sheet Set",                199900,   799900),
    ("Home",        "Pressure Cooker",              199900,   799900),
    ("Home",        "Electric Kettle",               79900,   299900),
    ("Books",       "Python Programming Guide",      29900,    79900),
    ("Books",       "Finance & Investing",           49900,   149900),
    ("Books",       "Business Strategy",             39900,   129900),
    ("Sports",      "Yoga Mat",                      49900,   299900),
    ("Sports",      "Cricket Bat",                  149900,   999900),
    ("Sports",      "Resistance Bands Set",           39900,   199900),
    ("Beauty",      "Face Serum",                    99900,   499900),
    ("Beauty",      "Sunscreen SPF50",               29900,   149900),
    ("Beauty",      "Hair Care Kit",                 79900,   399900),
]

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]
PAYMENT_WEIGHTS = [32, 48, 15, 5]

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — ORDERS (400 total)
# ─────────────────────────────────────────────────────────────────────────────
#
# Bucket layout (by index 0-399):
#   [0   – 289]  290 → NORMAL PAID   (will get captured payment + settlement)
#   [290 – 299]   10 → PAID but payment record MISSING (exception)
#   [300 – 304]    5 → PAID but payment AMOUNT MISMATCH (exception)
#   [305 – 314]   10 → PAID but payment FAILED (exception)
#   [315 – 319]    5 → PAID, duplicate attempt: 1 failed + 1 captured (exception)
#   [320 – 349]   30 → PROCESSING (some have pending payments)
#   [350 – 369]   20 → CANCELLED (no payment)
#   [370 – 399]   30 → FAILED (no payment)

print("Generating orders...")

orders = []
order_buckets = {
    "normal":       list(range(0,   290)),
    "missing_pmt":  list(range(290, 300)),
    "mismatch":     list(range(300, 305)),
    "failed_pmt":   list(range(305, 315)),
    "duplicate":    list(range(315, 320)),
    "processing":   list(range(320, 350)),
    "cancelled":    list(range(350, 370)),
    "failed":       list(range(370, 400)),
}

for i in range(400):
    order_id = f"ORD-{10001 + i}"
    cust = random.choice(CUSTOMER_IDS)
    prod = random.choice(PRODUCTS)
    amount = random.randrange(prod[2], prod[3], 100)    # multiple of 100 paise
    odate  = rnd_date(START, END)
    method = random.choices(PAYMENT_METHODS, PAYMENT_WEIGHTS)[0]

    if i in order_buckets["normal"]:
        status = "paid"
    elif i in order_buckets["missing_pmt"] or i in order_buckets["mismatch"] \
            or i in order_buckets["failed_pmt"] or i in order_buckets["duplicate"]:
        status = "paid"
    elif i in order_buckets["processing"]:
        status = "processing"
    elif i in order_buckets["cancelled"]:
        status = "cancelled"
    else:
        status = "failed"

    orders.append({
        "order_id":     order_id,
        "customer_id":  cust,
        "order_amount": amount,
        "currency":     "INR",
        "order_date":   fmt(odate),
        "payment_mode": method,
        "order_status": status,
        "created_at":   fmt(odate),
    })

print(f"  → {len(orders)} orders")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — PAYMENTS
# ─────────────────────────────────────────────────────────────────────────────

print("Generating payments...")

payments = []
# We'll track which payment_ids are captured and should go into settlements
captured_payment_ids     = []   # (payment_id, order_id, amount, captured_at)
# Payments that should NOT be in any settlement (exception case)
no_settlement_payment_ids = []

def make_payment_id() -> str:
    return f"pay_{rnd_alphanum(14)}"

# ── 2a: Normal captured payments (orders 0-289) ─────────────────────────────
for i in order_buckets["normal"]:
    o = orders[i]
    pid = make_payment_id()
    cap_dt = datetime.strptime(o["order_date"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(1, 20))
    rec = {
        "payment_id":          pid,
        "order_id":            o["order_id"],
        "amount":              o["order_amount"],
        "currency":            "INR",
        "status":              "captured",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": fmt(cap_dt),
        "created_at":          fmt(cap_dt),
    }
    payments.append(rec)
    # First 5 of the 290 will be "not in any settlement" (exception)
    if i < 5:
        no_settlement_payment_ids.append(pid)
    else:
        captured_payment_ids.append((pid, o["order_id"], o["order_amount"], cap_dt))

# ── 2b: Orders 290-299: PAID but no payment record ─────────────────────────
# (nothing to append — exception is the absence of a payment)

# ── 2c: Orders 300-304: PAYMENT AMOUNT MISMATCH ────────────────────────────
for i in order_buckets["mismatch"]:
    o = orders[i]
    pid = make_payment_id()
    original = o["order_amount"]
    # Deviate by ±2-5%
    delta = random.randint(int(original * 0.02), int(original * 0.05))
    wrong_amount = original - delta if random.random() < 0.6 else original + delta
    cap_dt = datetime.strptime(o["order_date"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(1, 20))
    payments.append({
        "payment_id":          pid,
        "order_id":            o["order_id"],
        "amount":              wrong_amount,
        "currency":            "INR",
        "status":              "captured",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": fmt(cap_dt),
        "created_at":          fmt(cap_dt),
    })
    captured_payment_ids.append((pid, o["order_id"], wrong_amount, cap_dt))

# ── 2d: Orders 305-314: FAILED PAYMENT ─────────────────────────────────────
for i in order_buckets["failed_pmt"]:
    o = orders[i]
    pid = make_payment_id()
    cap_dt = datetime.strptime(o["order_date"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(1, 30))
    payments.append({
        "payment_id":          pid,
        "order_id":            o["order_id"],
        "amount":              o["order_amount"],
        "currency":            "INR",
        "status":              "failed",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": "",       # CSV null
        "created_at":          fmt(cap_dt),
    })
    # Failed payments do NOT go into settlements

# ── 2e: Orders 315-319: DUPLICATE ATTEMPT (1 failed + 1 captured) ──────────
for i in order_buckets["duplicate"]:
    o = orders[i]
    odate = datetime.strptime(o["order_date"], "%Y-%m-%d %H:%M:%S")
    # First attempt — failed
    pid_fail = make_payment_id()
    payments.append({
        "payment_id":          pid_fail,
        "order_id":            o["order_id"],
        "amount":              o["order_amount"],
        "currency":            "INR",
        "status":              "failed",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": "",
        "created_at":          fmt(odate + timedelta(minutes=2)),
    })
    # Second attempt — captured
    pid_ok = make_payment_id()
    cap_dt = odate + timedelta(minutes=random.randint(15, 60))
    payments.append({
        "payment_id":          pid_ok,
        "order_id":            o["order_id"],
        "amount":              o["order_amount"],
        "currency":            "INR",
        "status":              "captured",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": fmt(cap_dt),
        "created_at":          fmt(cap_dt),
    })
    captured_payment_ids.append((pid_ok, o["order_id"], o["order_amount"], cap_dt))

# ── 2f: ORPHAN payments (no matching order) ─────────────────────────────────
for _ in range(8):
    pid = make_payment_id()
    amount = random.randrange(50000, 2000000, 100)
    cap_dt = rnd_date(START, END)
    payments.append({
        "payment_id":          pid,
        "order_id":            "",        # No matching order
        "amount":              amount,
        "currency":            "INR",
        "status":              "captured",
        "payment_method":      random.choices(PAYMENT_METHODS, PAYMENT_WEIGHTS)[0],
        "payment_captured_at": fmt(cap_dt),
        "created_at":          fmt(cap_dt),
    })
    captured_payment_ids.append((pid, None, amount, cap_dt))

# ── 2g: PENDING payments for PROCESSING orders ─────────────────────────────
for i in order_buckets["processing"][:15]:   # 15 of 30 processing orders
    o = orders[i]
    pid = make_payment_id()
    created = datetime.strptime(o["order_date"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=5)
    payments.append({
        "payment_id":          pid,
        "order_id":            o["order_id"],
        "amount":              o["order_amount"],
        "currency":            "INR",
        "status":              "pending",
        "payment_method":      o["payment_mode"],
        "payment_captured_at": "",
        "created_at":          fmt(created),
    })

print(f"  → {len(payments)} payments ({len(captured_payment_ids)} captured, eligible for settlement)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — SETTLEMENTS (35 total)
# ─────────────────────────────────────────────────────────────────────────────
#
# Group captured payments (excluding the 5 "not-in-settlement" ones) into
# weekly settlement batches.
#
# Exception cases:
#   - 4 settlements: NO bank credit
#   - 2 settlements: bank amount MISMATCH
#   - 3 settlements: DELAYED bank credit

print("Generating settlements...")

# Only payments that should be settled
settleable = [(pid, oid, amt, dt) for (pid, oid, amt, dt) in captured_payment_ids]
# Sort by captured_at for grouping
settleable.sort(key=lambda x: x[3])

# Split into 35 groups (roughly equal)
NUM_SETTLEMENTS = 35
groups = [[] for _ in range(NUM_SETTLEMENTS)]
for idx, item in enumerate(settleable):
    groups[idx % NUM_SETTLEMENTS].append(item)

settlements     = []
settlement_lines = []
# (settlement_id, settlement_utr, net_amount, settlement_date, bank_exception)
settlement_meta = []

# Exception assignment (by settlement index)
NO_BANK_CREDIT_IDX     = {2, 7, 18, 29}       # 4 settlements
AMOUNT_MISMATCH_IDX    = {5, 22}               # 2 settlements
DELAYED_CREDIT_IDX     = {10, 15, 27}          # 3 settlements

for s_idx, group in enumerate(groups):
    if not group:
        continue

    sid  = f"SETL-{9001 + s_idx}"
    utr  = f"UTR{random.randint(100000000000, 999999999999)}"

    # Settlement date = 1 business day after the last captured payment
    last_cap_date = max(dt for _, _, _, dt in group)
    s_date = last_cap_date + timedelta(days=1)

    # Compute financial totals using integer paise arithmetic
    gross = sum(amt for _, _, amt, _ in group)
    fee   = calc_fee(gross)
    tax   = calc_tax(fee)
    net   = gross - fee - tax

    # Determine bank-side exception type
    if s_idx in NO_BANK_CREDIT_IDX:
        bank_exc = "NO_BANK_CREDIT"
    elif s_idx in AMOUNT_MISMATCH_IDX:
        bank_exc = "AMOUNT_MISMATCH"
    elif s_idx in DELAYED_CREDIT_IDX:
        bank_exc = "DELAYED"
    else:
        bank_exc = "NORMAL"

    settlements.append({
        "settlement_id":     sid,
        "settlement_date":   fmt(s_date),
        "gross_amount":      gross,
        "fee_amount":        fee,
        "tax_amount":        tax,
        "adjustment_amount": 0,
        "net_amount":        net,
        "settlement_utr":    utr,
        "status":            "settled",
        "created_at":        fmt(s_date),
    })

    settlement_meta.append((sid, utr, net, s_date, bank_exc))

    # Settlement lines: one per payment in this group
    for pid, oid, amt, _ in group:
        line_fee = calc_fee(amt)
        line_tax = calc_tax(line_fee)
        line_net = amt - line_fee - line_tax
        settlement_lines.append({
            "settlement_id": sid,
            "payment_id":    pid,
            "amount":        amt,
            "fee":           line_fee,
            "tax":           line_tax,
            "net_amount":    line_net,
        })

print(f"  → {len(settlements)} settlements, {len(settlement_lines)} settlement lines")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BANK TRANSACTIONS (~60 total)
# ─────────────────────────────────────────────────────────────────────────────
#
# Sources:
#   - Settlement credits: matched (NORMAL / DELAYED / MISMATCH) — ~28 entries
#   - NO_BANK_CREDIT settlements: skipped
#   - Orphan bank credits (no settlement): 4 entries
#   - Miscellaneous debits (vendor payments, fees, etc.): 15 entries
#   - Other bank credits (interest, refunds from vendors): 10 entries

print("Generating bank transactions...")

bank_txns  = []
bank_idx   = 1

def bank_id() -> str:
    global bank_idx
    bid = f"BANK-{str(bank_idx).zfill(4)}"
    bank_idx += 1
    return bid

# ── 4a: Settlement-linked bank credits ─────────────────────────────────────
for (sid, utr, net, s_date, bank_exc) in settlement_meta:
    if bank_exc == "NO_BANK_CREDIT":
        continue    # Exception: no bank entry for this settlement

    if bank_exc == "DELAYED":
        credit_date = s_date + timedelta(days=random.randint(8, 14))
    else:
        credit_date = s_date + timedelta(days=random.randint(1, 2))

    if bank_exc == "AMOUNT_MISMATCH":
        # Mismatch: deviate by ₹100–₹500
        delta = random.randint(10000, 50000)
        credit_amount = net - delta
    else:
        credit_amount = net

    narration = f"NEFT CR {utr} RAZORPAY PAYMENTS LTD"

    bank_txns.append({
        "bank_entry_id":    bank_id(),
        "bank_date":        fmt(credit_date),
        "amount":           credit_amount,
        "direction":        "CREDIT",
        "narration":        narration,
        "utr":              utr,
        "transaction_type": "SETTLEMENT",
        "created_at":       fmt(credit_date),
    })

# ── 4b: ORPHAN bank credits (no matching settlement) ───────────────────────
for k in range(4):
    orphan_dt = rnd_date(START, END)
    fake_utr  = f"UTR{random.randint(100000000000, 999999999999)}"
    orphan_amt = random.randrange(500000, 5000000, 100)
    bank_txns.append({
        "bank_entry_id":    bank_id(),
        "bank_date":        fmt(orphan_dt),
        "amount":           orphan_amt,
        "direction":        "CREDIT",
        "narration":        f"NEFT CR {fake_utr} UNKNOWN SENDER",
        "utr":              fake_utr,
        "transaction_type": "SETTLEMENT",
        "created_at":       fmt(orphan_dt),
    })

# ── 4c: Miscellaneous DEBIT transactions ───────────────────────────────────
DEBIT_NARRATIONS = [
    ("VENDOR PAYMENT - PACKAGING SUPPLIES", "VENDOR"),
    ("NEFT DR - WAREHOUSE RENT", "VENDOR"),
    ("PLATFORM FEE - MARKETPLACE", "FEE"),
    ("TDS PAYMENT - GOVT", "TAX"),
    ("SALARY CREDIT - STAFF", "SALARY"),
    ("AWS CLOUD SERVICES", "INFRA"),
    ("COURIER SERVICE PAYMENT", "VENDOR"),
    ("ELECTRICITY BILL PAYMENT", "UTILITY"),
    ("INTERNET & PHONE BILL", "UTILITY"),
    ("GST PAYMENT - GOVT", "TAX"),
    ("OFFICE SUPPLIES PURCHASE", "VENDOR"),
    ("INSURANCE PREMIUM PAYMENT", "INSURANCE"),
    ("ADVERTISING - META ADS", "MARKETING"),
    ("ADVERTISING - GOOGLE ADS", "MARKETING"),
    ("SUBSCRIPTION - SAAS TOOLS", "INFRA"),
]
random.shuffle(DEBIT_NARRATIONS)
for narration, ttype in DEBIT_NARRATIONS:
    dt = rnd_date(START, END)
    amount = random.randrange(50000, 2000000, 100)
    bank_txns.append({
        "bank_entry_id":    bank_id(),
        "bank_date":        fmt(dt),
        "amount":           amount,
        "direction":        "DEBIT",
        "narration":        narration,
        "utr":              "",
        "transaction_type": ttype,
        "created_at":       fmt(dt),
    })

# ── 4d: Other CREDIT transactions (interest, refunds from vendors) ──────────
OTHER_CREDITS = [
    ("INTEREST CREDIT - SAVINGS ACCOUNT", "INTEREST"),
    ("REFUND FROM VENDOR - PACKAGING", "REFUND"),
    ("REFUND FROM COURIER PARTNER", "REFUND"),
    ("BANK CASH BACK", "CASHBACK"),
    ("SECURITY DEPOSIT REFUND", "REFUND"),
    ("INTEREST CREDIT - FD", "INTEREST"),
    ("ADVANCE REFUND - SUPPLIER", "REFUND"),
    ("FESTIVAL BONUS CREDIT", "BONUS"),
    ("AFFILIATE COMMISSION CREDIT", "COMMISSION"),
    ("INSURANCE CLAIM SETTLED", "INSURANCE"),
]
for narration, ttype in OTHER_CREDITS:
    dt = rnd_date(START, END)
    amount = random.randrange(10000, 500000, 100)
    bank_txns.append({
        "bank_entry_id":    bank_id(),
        "bank_date":        fmt(dt),
        "amount":           amount,
        "direction":        "CREDIT",
        "narration":        narration,
        "utr":              "",
        "transaction_type": ttype,
        "created_at":       fmt(dt),
    })

print(f"  → {len(bank_txns)} bank transactions")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — GROUND TRUTH CSV
# ─────────────────────────────────────────────────────────────────────────────
#
# WARNING: This file is for DEVELOPER TESTING ONLY.
# The application must NOT load this into the production database.

print("Generating ground truth...")

ground_truth = []

# ── Orders ──────────────────────────────────────────────────────────────────
for i in order_buckets["normal"]:
    o = orders[i]
    if i < 5:   # payments exist but not in any settlement
        ground_truth.append({
            "entity_type":            "ORDER",
            "entity_id":              o["order_id"],
            "expected_related_id":    "",
            "expected_status":        "PAYMENT_NOT_IN_SETTLEMENT",
            "expected_difference":    0,
            "expected_exception_type": "PAYMENT_NOT_IN_SETTLEMENT",
        })
    else:
        ground_truth.append({
            "entity_type":            "ORDER",
            "entity_id":              o["order_id"],
            "expected_related_id":    "",
            "expected_status":        "MATCHED",
            "expected_difference":    0,
            "expected_exception_type": "NONE",
        })

for i in order_buckets["missing_pmt"]:
    o = orders[i]
    ground_truth.append({
        "entity_type":            "ORDER",
        "entity_id":              o["order_id"],
        "expected_related_id":    "",
        "expected_status":        "PAYMENT_MISSING",
        "expected_difference":    o["order_amount"],
        "expected_exception_type": "ORDER_WITHOUT_PAYMENT",
    })

for i in order_buckets["mismatch"]:
    o = orders[i]
    ground_truth.append({
        "entity_type":            "ORDER",
        "entity_id":              o["order_id"],
        "expected_related_id":    "",
        "expected_status":        "AMOUNT_MISMATCH",
        "expected_difference":    "",
        "expected_exception_type": "PAYMENT_AMOUNT_MISMATCH",
    })

for i in order_buckets["failed_pmt"]:
    o = orders[i]
    ground_truth.append({
        "entity_type":            "ORDER",
        "entity_id":              o["order_id"],
        "expected_related_id":    "",
        "expected_status":        "PAYMENT_FAILED",
        "expected_difference":    o["order_amount"],
        "expected_exception_type": "FAILED_PAYMENT",
    })

for i in order_buckets["duplicate"]:
    o = orders[i]
    ground_truth.append({
        "entity_type":            "ORDER",
        "entity_id":              o["order_id"],
        "expected_related_id":    "",
        "expected_status":        "DUPLICATE_PAYMENT_ATTEMPT",
        "expected_difference":    0,
        "expected_exception_type": "DUPLICATE_PAYMENT",
    })

# ── Orphan payments ──────────────────────────────────────────────────────────
for p in payments:
    if p["order_id"] == "" and p["status"] == "captured":
        ground_truth.append({
            "entity_type":            "PAYMENT",
            "entity_id":              p["payment_id"],
            "expected_related_id":    "",
            "expected_status":        "ORPHAN_PAYMENT",
            "expected_difference":    p["amount"],
            "expected_exception_type": "PAYMENT_WITHOUT_ORDER",
        })

# ── Payments not in any settlement ──────────────────────────────────────────
for pid in no_settlement_payment_ids:
    ground_truth.append({
        "entity_type":            "PAYMENT",
        "entity_id":              pid,
        "expected_related_id":    "",
        "expected_status":        "NOT_IN_SETTLEMENT",
        "expected_difference":    "",
        "expected_exception_type": "PAYMENT_NOT_IN_SETTLEMENT",
    })

# ── Settlement exceptions ────────────────────────────────────────────────────
for s_idx, (sid, utr, net, s_date, bank_exc) in enumerate(settlement_meta):
    if bank_exc == "NO_BANK_CREDIT":
        ground_truth.append({
            "entity_type":            "SETTLEMENT",
            "entity_id":              sid,
            "expected_related_id":    "",
            "expected_status":        "SETTLEMENT_MISSING_IN_BANK",
            "expected_difference":    net,
            "expected_exception_type": "SETTLEMENT_MISSING_IN_BANK",
        })
    elif bank_exc == "AMOUNT_MISMATCH":
        ground_truth.append({
            "entity_type":            "SETTLEMENT",
            "entity_id":              sid,
            "expected_related_id":    "",
            "expected_status":        "BANK_AMOUNT_MISMATCH",
            "expected_difference":    "",
            "expected_exception_type": "SETTLEMENT_BANK_AMOUNT_MISMATCH",
        })
    elif bank_exc == "DELAYED":
        ground_truth.append({
            "entity_type":            "SETTLEMENT",
            "entity_id":              sid,
            "expected_related_id":    "",
            "expected_status":        "DELAYED_BANK_CREDIT",
            "expected_difference":    0,
            "expected_exception_type": "DELAYED_BANK_CREDIT",
        })
    else:
        ground_truth.append({
            "entity_type":            "SETTLEMENT",
            "entity_id":              sid,
            "expected_related_id":    utr,
            "expected_status":        "MATCHED",
            "expected_difference":    0,
            "expected_exception_type": "NONE",
        })

print(f"  → {len(ground_truth)} ground truth records")

# ─────────────────────────────────────────────────────────────────────────────
# WRITE CSV FILES
# ─────────────────────────────────────────────────────────────────────────────

def write_csv(filepath: str, rows: list, fieldnames: list) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):>5} rows → {os.path.relpath(filepath)}")

print("\nWriting CSV files...")

write_csv(
    os.path.join(DEMO_DIR, "orders.csv"),
    orders,
    ["order_id", "customer_id", "order_amount", "currency", "order_date", "payment_mode", "order_status", "created_at"],
)

write_csv(
    os.path.join(DEMO_DIR, "payments.csv"),
    payments,
    ["payment_id", "order_id", "amount", "currency", "status", "payment_method", "payment_captured_at", "created_at"],
)

write_csv(
    os.path.join(DEMO_DIR, "settlements.csv"),
    settlements,
    ["settlement_id", "settlement_date", "gross_amount", "fee_amount", "tax_amount", "adjustment_amount", "net_amount", "settlement_utr", "status", "created_at"],
)

write_csv(
    os.path.join(DEMO_DIR, "settlement_lines.csv"),
    settlement_lines,
    ["settlement_id", "payment_id", "amount", "fee", "tax", "net_amount"],
)

write_csv(
    os.path.join(DEMO_DIR, "bank_statement.csv"),
    bank_txns,
    ["bank_entry_id", "bank_date", "amount", "direction", "narration", "utr", "transaction_type", "created_at"],
)

write_csv(
    os.path.join(GT_DIR, "ground_truth.csv"),
    ground_truth,
    ["entity_type", "entity_id", "expected_related_id", "expected_status", "expected_difference", "expected_exception_type"],
)

print("\n✓ Demo data generation complete!")
print(f"  Orders:           {len(orders)}")
print(f"  Payments:         {len(payments)}")
print(f"  Settlements:      {len(settlements)}")
print(f"  Settlement lines: {len(settlement_lines)}")
print(f"  Bank transactions:{len(bank_txns)}")
print(f"  Ground truth:     {len(ground_truth)}")
