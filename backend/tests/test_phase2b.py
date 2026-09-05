"""
Phase 2B Automated Test Suite — Financial Intelligence & Investigation System

Tests:
  1. Unit: Prioritization engine evaluates value at risk, age, and risk tiers (CRITICAL, HIGH, MEDIUM, LOW).
  2. Unit: Paid-but-unfulfilled detector flags orders captured > 72h without shipment.
  3. Unit: Settlement-missing-in-bank detector flags settlements > 48h without bank credit.
  4. Unit: Money lineage builder returns valid nodes, edges, visual statuses, and handles missing links.
  5. Integration: Full detection engine runs against database and populates FinancialException table.

Run:
  cd backend
  python tests/test_phase2b.py
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.models import Order, Payment, Shipment, Settlement, BankTransaction, FinancialException
from app.services.exceptions.prioritizer import calculate_exception_priority
from app.services.exceptions.detectors import (
    detect_paid_but_unfulfilled,
    detect_settlement_missing_in_bank,
    run_all_exception_detection,
)
from app.services.lineage.builder import build_money_lineage_graph


# ============================================================================
# Unit Tests — Detectors & Risk Assessment
# ============================================================================

def test_risk_prioritization():
    print("Testing risk level evaluation...")
    # CRITICAL: High value (e.g. ₹50,000 = 5,000,000 paise) + old age (e.g. 150 hours)
    risk_level, score = calculate_exception_priority(
        value_at_risk_paise=5_000_000,
        elapsed_hours=150.0,
        exception_type="SETTLEMENT_MISSING_IN_BANK",
    )
    assert risk_level == "CRITICAL", f"Expected CRITICAL, got {risk_level} (score: {score})"
    assert score >= 70

    # HIGH: ₹25,000 = 2,500,000 paise, moderate age
    risk_level, score = calculate_exception_priority(
        value_at_risk_paise=2_500_000,
        elapsed_hours=50.0,
        exception_type="PAID_BUT_UNFULFILLED",
    )
    assert risk_level in ("CRITICAL", "HIGH"), f"Expected HIGH/CRITICAL, got {risk_level} (score: {score})"

    # LOW: small value (₹500 = 50,000 paise) and recent
    risk_level, score = calculate_exception_priority(
        value_at_risk_paise=50_000,
        elapsed_hours=10.0,
        exception_type="CALCULATION_DISCREPANCY",
    )
    assert risk_level == "LOW", f"Expected LOW, got {risk_level} (score: {score})"
    assert score < 30

    print("  [PASS] Risk prioritization evaluated correctly across tiers.")


def test_unfulfilled_detector_logic():
    print("Testing paid-but-unfulfilled detector logic...")
    db = SessionLocal()
    try:
        exceptions = detect_paid_but_unfulfilled(db, threshold_hours=72)

        # In our demo dataset, ORD-10021 is unfulfilled
        order_ids = [e.related_order_id for e in exceptions]
        assert "ORD-10021" in order_ids, f"Expected ORD-10021 in {order_ids}"

        # Find the specific exception for ORD-10021
        exc = next(e for e in exceptions if e.related_order_id == "ORD-10021")
        assert exc.suggested_owner == "Operations"
        assert exc.exception_type == "PAID_BUT_UNFULFILLED"
        assert exc.value_at_risk > 0
        assert "ORD-10021" in exc.explanation
        assert exc.evidence["order_id"] == "ORD-10021"
        assert exc.evidence["payment_id"].startswith("pay_")
        print(f"  [PASS] Paid-but-unfulfilled detected: {len(exceptions)} cases (including ORD-10021).")
    finally:
        db.close()


def test_settlement_missing_detector_logic():
    print("Testing settlement-missing-in-bank detector logic...")
    db = SessionLocal()
    try:
        exceptions = detect_settlement_missing_in_bank(db, window_hours=48)

        # SETL-9003 has no bank match in demo data
        settlement_ids = [e.related_settlement_id for e in exceptions]
        assert "SETL-9003" in settlement_ids, f"Expected SETL-9003 in {settlement_ids}"

        exc = next(e for e in exceptions if e.related_settlement_id == "SETL-9003")
        assert exc.suggested_owner == "Finance"
        assert exc.exception_type == "SETTLEMENT_MISSING_IN_BANK"
        assert exc.value_at_risk > 0
        assert "SETL-9003" in exc.explanation
        print(f"  [PASS] Settlement-missing-in-bank detected: {len(exceptions)} cases (including SETL-9003).")
    finally:
        db.close()


def test_money_lineage_graph():
    print("Testing Money Lineage Graph builder...")
    db = SessionLocal()
    try:
        # 1. Test order lineage graph structure
        graph = build_money_lineage_graph(db, "order", "ORD-10001")
        assert graph["summary"]["status"] in ("VERIFIED", "AT_RISK")
        assert len(graph["nodes"]) >= 6  # order, payment, fee, gst, settlement, bank, shipment

        # Verify visual statuses and categories
        categories = {n["data"]["category"] for n in graph["nodes"]}
        assert "ORDER" in categories
        assert "PAYMENT" in categories
        assert "SETTLEMENT" in categories
        assert "BANK_CREDIT" in categories
        assert "SHIPMENT" in categories

        # 2. Test unfulfilled order (ORD-10021) — missing shipment node must be present with is_missing=True
        graph_unfulfilled = build_money_lineage_graph(db, "order", "ORD-10021")
        assert graph_unfulfilled["summary"]["status"] == "AT_RISK"
        assert graph_unfulfilled["summary"]["complete"] is False

        missing_shipment = next(
            (n for n in graph_unfulfilled["nodes"] if n["data"]["category"] == "SHIPMENT"), None
        )
        assert missing_shipment is not None, "Expected missing shipment node in graph"
        assert missing_shipment["data"]["is_missing"] is True
        assert missing_shipment["data"]["visual_status"] in ("red", "grey")

        # 3. Test settlement lineage (SETL-9001)
        graph_settlement = build_money_lineage_graph(db, "settlement", "SETL-9001")
        assert len(graph_settlement["nodes"]) >= 4
        assert graph_settlement["root_entity"]["id"] == "SETL-9001"

        print(f"  [PASS] Money Lineage Graph verified: normal, unfulfilled, and settlement journeys.")
    finally:
        db.close()


def test_database_detection_pipeline():
    print("Testing end-to-end exception detection and database caching...")
    db = SessionLocal()
    try:
        result = run_all_exception_detection(db)

        assert result["total_exceptions"] > 0
        assert "PAID_BUT_UNFULFILLED" in result["by_type"]
        assert "SETTLEMENT_MISSING_IN_BANK" in result["by_type"]

        # Check that records were saved in financial_exceptions table
        db_records = db.query(FinancialException).all()
        assert len(db_records) == result["total_exceptions"]

        # Verify a specific record has proper columns
        sample = db_records[0]
        assert sample.case_id.startswith("CASE-")
        assert sample.risk_level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert sample.status in ("OPEN", "ASSIGNED", "IN_REVIEW", "RESOLVED", "DISMISSED", "ESCALATED")
        assert sample.suggested_owner in ("Finance", "Operations", "Support")
        assert sample.value_at_risk > 0
        assert len(sample.explanation) > 10
        assert len(sample.triggering_rule) > 5

        print(f"  [PASS] Database cached {len(db_records)} investigation cases with complete evidence.")
    finally:
        db.close()


def run_all_tests():
    print("\n==================================================")
    print("RUNNING PHASE 2B AUTOMATED TEST SUITE")
    print("==================================================")

    test_risk_prioritization()
    test_unfulfilled_detector_logic()
    test_settlement_missing_detector_logic()
    test_money_lineage_graph()
    test_database_detection_pipeline()

    print("\n==================================================")
    print("ALL PHASE 2B TESTS PASSED SUCCESSFULLY (5/5)!")
    print("==================================================\n")


if __name__ == "__main__":
    run_all_tests()
