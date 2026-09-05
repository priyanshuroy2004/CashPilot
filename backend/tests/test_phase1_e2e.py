"""
Complete Phase 1 End-to-End Test Suite for CASHpilot AI.

Tests all 11 requirements:
TEST 1: Load demo data.
TEST 2: Verify database counts.
TEST 3: Run reconciliation.
TEST 4: Verify matched records.
TEST 5: Verify known synthetic anomalies appear as exceptions.
TEST 6: Verify dashboard totals.
TEST 7: Upload a valid CSV dataset.
TEST 8: Upload invalid CSV.
TEST 9: Verify validation errors.
TEST 10: Open an exception and verify details.
TEST 11: Verify no dashboard numbers are hardcoded.
"""
import io
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

API_BASE = "http://localhost:8000"


def http_get(path: str) -> dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post(path: str, data: dict = None, form_data: bytes = None, content_type: str = "application/json") -> dict:
    url = f"{API_BASE}{path}"
    headers = {"Accept": "application/json"}
    if form_data is not None:
        headers["Content-Type"] = content_type
        body = form_data
    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        headers["Content-Type"] = "application/json"
        body = b""

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_e2e_tests():
    print("==================================================")
    print("RUNNING CASHpilot AI PHASE 1 END-TO-END TEST SUITE")
    print("==================================================")

    # ---------------------------------------------------------------------------
    # TEST 1: Load Demo Data
    # ---------------------------------------------------------------------------
    print("\n[TEST 1] Loading Demo Merchant Data...")
    load_res = http_post("/api/demo/load")
    assert load_res["success"] is True, "Demo load failed"
    print(f"  [OK] Demo data loaded: {load_res['orders']} orders, {load_res['payments']} payments, {load_res['settlements']} settlements.")

    # ---------------------------------------------------------------------------
    # TEST 2: Verify Database Counts
    # ---------------------------------------------------------------------------
    print("\n[TEST 2] Verifying Database Counts...")
    status_res = http_get("/api/demo/status")
    assert status_res["orders"] == 400, f"Expected 400 orders, got {status_res['orders']}"
    assert status_res["payments"] == 338, f"Expected 338 payments, got {status_res['payments']}"
    assert status_res["settlements"] == 35, f"Expected 35 settlements, got {status_res['settlements']}"
    assert status_res["settlement_lines"] == 303, f"Expected 303 settlement lines, got {status_res['settlement_lines']}"
    assert status_res["bank_transactions"] == 60, f"Expected 60 bank txs, got {status_res['bank_transactions']}"
    print(f"  [OK] All database counts verified: orders={status_res['orders']}, payments={status_res['payments']}, settlements={status_res['settlements']}, bank_txs={status_res['bank_transactions']}")

    # ---------------------------------------------------------------------------
    # TEST 3: Run Reconciliation
    # ---------------------------------------------------------------------------
    print("\n[TEST 3] Running Deterministic Reconciliation Engine...")
    recon_res = http_post("/api/reconciliation/run?tolerance_paise=1")
    assert recon_res["success"] is True, "Reconciliation execution failed"
    assert recon_res["total_records"] > 0, "No records processed"
    print(f"  [OK] Reconciliation run completed: {recon_res['total_records']} total records processed.")

    # ---------------------------------------------------------------------------
    # TEST 4: Verify Matched Records
    # ---------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Matched Records...")
    summary = http_get("/api/reconciliation/summary")
    op_matched = summary["orders_payments"]["matched"]
    sb_matched = summary["settlements_bank"]["matched"]
    assert op_matched == 290, f"Expected 290 matched orders, got {op_matched}"
    assert sb_matched == 29, f"Expected 29 matched settlements, got {sb_matched}"
    
    # Query matched orders
    matched_orders = http_get("/api/reconciliation/orders-payments?status=MATCHED&limit=5")
    assert len(matched_orders["items"]) > 0, "No matched items returned"
    for item in matched_orders["items"]:
        assert item["status"] == "MATCHED"
        assert item["difference"] == 0
    print(f"  [OK] Matched records verified: {op_matched} orders/payments, {sb_matched} settlements/bank.")

    # ---------------------------------------------------------------------------
    # TEST 5: Verify Known Synthetic Anomalies Appear as Exceptions
    # ---------------------------------------------------------------------------
    print("\n[TEST 5] Verifying Synthetic Anomalies as Exceptions...")
    exc_sum = http_get("/api/exceptions/summary")
    assert exc_sum["total_exceptions"] == 124, f"Expected 124 exceptions, got {exc_sum['total_exceptions']}"
    assert "PAYMENT_MISSING" in exc_sum["by_type"]
    assert "PAYMENT_AMOUNT_MISMATCH" in exc_sum["by_type"]
    assert "FAILED_PAYMENT" in exc_sum["by_type"]
    assert "SETTLEMENT_MISSING_IN_BANK" in exc_sum["by_type"]
    assert "SETTLEMENT_AMOUNT_MISMATCH" in exc_sum["by_type"]
    print(f"  [OK] All anomaly types verified: {exc_sum['by_type']}")

    # ---------------------------------------------------------------------------
    # TEST 6: Verify Dashboard Totals (Calculated from DB)
    # ---------------------------------------------------------------------------
    print("\n[TEST 6] Verifying Dashboard Overview Totals from DB...")
    dash = http_get("/api/dashboard/overview")
    assert dash["has_data"] is True
    assert dash["total_orders"] == 400
    assert dash["total_orders_amount"] > 0
    assert dash["total_captured_payments"] > 0
    assert dash["total_settlements"] == 35
    assert dash["total_bank_credits"] > 0
    assert dash["matched_records"] == 319  # 290 + 29
    assert dash["exception_count"] == 124
    assert dash["value_at_risk"] > 0
    print(f"  [OK] Dashboard KPIs calculated live: total_orders={dash['total_orders']}, matched={dash['matched_records']}, exceptions={dash['exception_count']}, value_at_risk=INR {dash['value_at_risk']/100:,.2f}")

    # ---------------------------------------------------------------------------
    # TEST 7: Upload a Valid CSV Dataset
    # ---------------------------------------------------------------------------
    print("\n[TEST 7] Uploading and Validating Valid CSV Dataset...")
    boundary = "----WebKitFormBoundaryE2ETest789"
    unique_sfx = datetime.now(timezone.utc).strftime("%H%M%S")
    valid_csv = (
        "order_id,customer_id,order_amount,currency,order_date,payment_mode,order_status\n"
        f"ORD-E2E-{unique_sfx}-1,CUST-001,1500.00,INR,2024-01-15 10:00:00,card,paid\n"
        f"ORD-E2E-{unique_sfx}-2,CUST-002,2500.00,INR,2024-01-15 11:00:00,upi,paid\n"
    )
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="orders_valid.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{valid_csv}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    upload_res = http_post("/api/data/upload", form_data=body, content_type=f"multipart/form-data; boundary={boundary}")
    assert len(upload_res["files"]) == 1
    f_res = upload_res["files"][0]
    assert f_res["dataset_type"] == "orders"
    assert f_res["row_count"] == 2
    assert f_res["error_count"] == 0
    print(f"  [OK] Valid CSV accepted: type={f_res['dataset_type']}, rows={f_res['row_count']}, errors={f_res['error_count']}")

    # ---------------------------------------------------------------------------
    # TEST 8 & 9: Upload Invalid CSV and Verify Validation Errors
    # ---------------------------------------------------------------------------
    print("\n[TEST 8 & 9] Uploading Invalid CSV & Verifying Validation Errors...")
    invalid_csv = (
        "order_id,customer_id,order_amount,currency,order_date,payment_mode,order_status\n"
        ",CUST-001,-50.00,INVALID_CURR,invalid_date,card,bad_status\n"
    )
    body_inv = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="orders_invalid.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{invalid_csv}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    upload_inv = http_post("/api/data/upload", form_data=body_inv, content_type=f"multipart/form-data; boundary={boundary}")
    assert len(upload_inv["files"]) == 1
    f_inv = upload_inv["files"][0]
    assert f_inv["error_count"] > 0, "Expected validation errors for invalid CSV"
    print(f"  [OK] Validation caught {f_inv['error_count']} schema & financial errors:")
    for err in f_inv["errors"][:3]:
        print(f"       - Row {err['row']} [{err['field']}]: {err['message']}")

    # ---------------------------------------------------------------------------
    # TEST 10: Open an Exception and Verify Details
    # ---------------------------------------------------------------------------
    print("\n[TEST 10] Opening Exception Drill-down Details...")
    exc_list = http_get("/api/exceptions?limit=1")
    assert len(exc_list["items"]) == 1
    test_exc = exc_list["items"][0]
    exc_id = test_exc["exception_id"]
    detail = http_get(f"/api/exceptions/{exc_id}")
    assert detail["exception_id"] == exc_id
    assert detail["severity"] in ("HIGH", "MEDIUM", "LOW")
    assert len(detail["methods_attempted"]) > 0
    assert detail["recommended_action"] is not None
    print(f"  [OK] Exception {exc_id} drill-down verified: type={detail['exception_type']}, severity={detail['severity']}, methods_attempted={len(detail['methods_attempted'])}, action='{detail['recommended_action']}'")

    # ---------------------------------------------------------------------------
    # TEST 11: Verify Dynamic (Non-hardcoded) Dashboard Numbers
    # ---------------------------------------------------------------------------
    print("\n[TEST 11] Verifying Dashboard Numbers are Dynamic...")
    # Verify numbers correlate with database queries and not constants
    assert dash["total_orders"] == status_res["orders"]
    assert dash["total_settlements"] == status_res["settlements"]
    assert dash["matched_records"] == (op_matched + sb_matched)
    print(f"  [OK] Dynamic calculations verified across DB tables.")

    print("\n==================================================")
    print("ALL 11 END-TO-END TESTS PASSED SUCCESSFULLY! [OK]")
    print("==================================================")


if __name__ == "__main__":
    run_e2e_tests()
