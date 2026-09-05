"""Quick E2E verification script for Phase 2A."""
import urllib.request, json, sys

BASE = "http://localhost:8000"

def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.loads(r.read())

def post(path):
    req = urllib.request.Request(BASE + path, method="POST", data=b"")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

print("=== Phase 2A E2E Verification ===")

try:
    # 1. Health
    h = get("/api/health")
    print(f"1. Health: {h['status']}")

    # 2. Load demo data
    print("2. Loading demo data...")
    d = post("/api/demo/load")
    print(f"   Orders={d['orders']}, Payments={d['payments']}, Settlements={d['settlements']}")
    print(f"   Refunds={d.get('refunds', 'N/A')}, Ledger={d.get('ledger_entries', 'N/A')}")

    # 3. Run Phase 1 reconciliation
    print("3. Running Phase 1 reconciliation...")
    r = post("/api/reconciliation/run")
    print(f"   Total records={r['total_records']}")

    # 4. Run Phase 2A engines
    print("4. Running Phase 2A financial engines...")
    f = post("/api/financial/run")
    calc = f["settlement_calculations"]
    tax = f["tax_reconciliation"]
    ref = f["refund_reconciliation"]
    print(f"   Settlement calc: total={calc['total']}, correct={calc['correct']}, discrepancy={calc['discrepancy']}")
    print(f"   Tax matching: total_checks={tax['total_checks']}, settlements={tax['settlements_checked']}")
    print(f"   Refund recon: total={ref['total_refunds']}, by_status={ref['by_status']}")

    # 5. Verify discrepancies exist
    disc = get("/api/financial/settlement-calculations?status=DISCREPANCY")
    print(f"5. DISCREPANCY settlements: {disc['total']}")
    for item in disc["items"][:2]:
        print(f"   {item['settlement_id']} reported={item['reported_net_inr']} expected={item['expected_net_inr']} diff={item['difference_inr']} INR")

    # 6. Verify tax anomalies
    tax_miss = get("/api/financial/tax-reconciliation?status=MISSING_LEDGER_ENTRY")
    tax_mismatch = get("/api/financial/tax-reconciliation?status=AMOUNT_MISMATCH")
    print(f"6. Tax MISSING_LEDGER_ENTRY: {tax_miss['total']}, AMOUNT_MISMATCH: {tax_mismatch['total']}")

    # 7. Verify refund statuses
    for status in ["REFUND_MATCHED", "REFUND_MISSING_IN_LEDGER", "DUPLICATE_REFUND", "REFUND_AMOUNT_MISMATCH", "REFUND_PENDING"]:
        r2 = get(f"/api/financial/refund-reconciliation?status={status}")
        print(f"7. Refunds {status}: {r2['total']}")

    # 8. Idempotency check — run again
    print("8. Idempotency check (re-running engines)...")
    f2 = post("/api/financial/run")
    assert f2["settlement_calculations"]["total"] == calc["total"], "Idempotency broken for settlement calcs"
    assert f2["refund_reconciliation"]["total_refunds"] == ref["total_refunds"], "Idempotency broken for refunds"
    print("   Idempotency OK")

    print()
    print("=" * 50)
    print("ALL PHASE 2A E2E CHECKS PASSED")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)
