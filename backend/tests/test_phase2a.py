"""
Phase 2A Automated Test Suite — Financial Intelligence Engine

Tests:
  1. Settlement Calculator — correct net calculation
  2. Settlement Calculator — discrepancy detection
  3. Settlement Calculator — refund adjustment
  4. Tax Matcher — all components matched
  5. Tax Matcher — GST missing in ledger
  6. Tax Matcher — fee amount mismatch
  7. Refund Matcher — fully matched refund
  8. Refund Matcher — missing in ledger
  9. Refund Matcher — duplicate refund in ledger
  10. Refund Matcher — amount mismatch
  11. Refund Matcher — pending refund (skips ledger check)
  12. Phase 1 regression — demo load + recon still works

Run:
  cd backend
  python -m pytest tests/test_phase2a.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock


# ============================================================================
# Unit tests for settlement_calculator (no DB needed)
# ============================================================================

class MockSettlement:
    def __init__(self, settlement_id, gross, fee, tax, adj, net):
        self.settlement_id = settlement_id
        self.gross_amount = gross
        self.fee_amount = fee
        self.tax_amount = tax
        self.adjustment_amount = adj
        self.net_amount = net


class MockSettlementLine:
    def __init__(self, sid, pid):
        self.settlement_id = sid
        self.payment_id = pid


class MockRefund:
    def __init__(self, rid, pid, sid, amount, status="processed"):
        self.refund_id = rid
        self.payment_id = pid
        self.settlement_id = sid
        self.amount = amount
        self.status = status


class MockLedgerEntry:
    def __init__(self, entry_id, entry_type, reference_id, amount):
        self.entry_id = entry_id
        self.entry_type = entry_type
        self.reference_id = reference_id
        self.amount = amount


def test_settlement_calculator_correct():
    """SETL-2A-001: 3 payments, correct fee/tax/net — should be CORRECT"""
    from app.services.financial_intelligence.settlement_calculator import calculate_settlement

    # gross=1800000, fee=36000, tax=6480, adj=0, net=1757520
    # expected_net = 1800000 - 36000 - 6480 - 0 + 0 = 1757520
    s = MockSettlement("SETL-2A-001", 1800000, 36000, 6480, 0, 1757520)
    lines = [MockSettlementLine("SETL-2A-001", f"pay_{i}") for i in range(3)]
    refunds = []

    result = calculate_settlement(s, lines, refunds)
    assert result["calculation_status"] == "CORRECT", f"Expected CORRECT, got {result['calculation_status']}"
    assert result["expected_net_amount"] == 1757520
    assert result["reported_net_amount"] == 1757520
    assert result["calculation_difference"] == 0
    assert result["payment_count"] == 3
    print("PASS test_settlement_calculator_correct")


def test_settlement_calculator_discrepancy():
    """SETL-2A-002: reported net is wrong — should be DISCREPANCY"""
    from app.services.financial_intelligence.settlement_calculator import calculate_settlement

    # gross=1000000, fee=20000, tax=3600, adj=0
    # correct_net = 1000000 - 20000 - 3600 = 976400
    # but reported as 930000 (wrong!) → difference = 930000 - 976400 = -46400
    s = MockSettlement("SETL-2A-002", 1000000, 20000, 3600, 0, 930000)
    lines = [MockSettlementLine("SETL-2A-002", f"pay_{i}") for i in range(2)]
    refunds = []

    result = calculate_settlement(s, lines, refunds)
    assert result["calculation_status"] == "DISCREPANCY", f"Expected DISCREPANCY, got {result['calculation_status']}"
    assert result["expected_net_amount"] == 976400
    assert result["reported_net_amount"] == 930000
    assert result["calculation_difference"] == -46400
    print("PASS test_settlement_calculator_discrepancy")


def test_settlement_calculator_refund_adjustment():
    """SETL-2A-003: settlement with refund deducted — should be CORRECT"""
    from app.services.financial_intelligence.settlement_calculator import calculate_settlement

    # gross=1000000, fee=30000, tax=5400, adj=200000 (refund deduction stored as positive adj)
    # reported_net = 764600
    # We have explicit refunds: 200000 paise processed
    # expected_net = 1000000 - 30000 - 5400 - 200000 = 764600
    s = MockSettlement("SETL-2A-003", 1000000, 30000, 5400, 200000, 764600)
    lines = [MockSettlementLine("SETL-2A-003", f"pay_{i}") for i in range(2)]
    refunds = [MockRefund("REF-X", "pay_0", "SETL-2A-003", 200000, "processed")]

    result = calculate_settlement(s, lines, refunds)
    assert result["refund_adjustment"] == 200000
    # With refunds provided, formula: gross - fee - tax - refund_adj + other_adj
    # = 1000000 - 30000 - 5400 - 200000 + 0 = 764600
    assert result["expected_net_amount"] == 764600
    assert result["reported_net_amount"] == 764600
    print("PASS test_settlement_calculator_refund_adjustment")


def test_settlement_calculator_zero_tax():
    """SETL-2A-004: no GST (tax=0) — should still calculate correctly"""
    from app.services.financial_intelligence.settlement_calculator import calculate_settlement

    # gross=1250000, fee=25000, tax=0, adj=0, net=1225000
    # expected_net = 1250000 - 25000 - 0 = 1225000
    s = MockSettlement("SETL-2A-004", 1250000, 25000, 0, 0, 1225000)
    lines = [MockSettlementLine("SETL-2A-004", f"pay_{i}") for i in range(2)]
    result = calculate_settlement(s, lines, [])
    assert result["calculation_status"] == "CORRECT"
    assert result["expected_net_amount"] == 1225000
    print("PASS test_settlement_calculator_zero_tax")


# ============================================================================
# Unit tests for tax_matcher
# ============================================================================

def test_tax_matcher_matched():
    """All components present in ledger with correct amounts → MATCHED"""
    from app.services.financial_intelligence.tax_matcher import _match_component

    fee_entry = MockLedgerEntry("LED-004", "FEE_EXPENSE", "SETL-9001", 112926)
    result = _match_component("SETL-9001", "FEE", 112926, [fee_entry])
    assert result["status"] == "MATCHED", f"Expected MATCHED, got {result['status']}"
    print("PASS test_tax_matcher_matched")


def test_tax_matcher_missing_ledger_entry():
    """TAX component with non-zero expected amount but no ledger entry → MISSING_LEDGER_ENTRY"""
    from app.services.financial_intelligence.tax_matcher import _match_component

    result = _match_component("SETL-2A-004", "TAX", 4500, [])  # No ledger entries
    assert result["status"] == "MISSING_LEDGER_ENTRY", f"Expected MISSING_LEDGER_ENTRY, got {result['status']}"
    print("PASS test_tax_matcher_missing_ledger_entry")


def test_tax_matcher_zero_component_no_ledger():
    """TAX component = 0, no ledger entry → MATCHED (zero means nothing expected)"""
    from app.services.financial_intelligence.tax_matcher import _match_component

    result = _match_component("SETL-2A-004", "TAX", 0, [])
    assert result["status"] == "MATCHED", f"Expected MATCHED for zero TAX with no ledger, got {result['status']}"
    print("PASS test_tax_matcher_zero_component_no_ledger")


def test_tax_matcher_amount_mismatch():
    """FEE entry present but amount differs → AMOUNT_MISMATCH"""
    from app.services.financial_intelligence.tax_matcher import _match_component

    fee_entry = MockLedgerEntry("LED-046", "FEE_EXPENSE", "SETL-2A-004", 20000)  # Ledger says 20000
    result = _match_component("SETL-2A-004", "FEE", 25000, [fee_entry])          # Expected 25000
    assert result["status"] == "AMOUNT_MISMATCH", f"Expected AMOUNT_MISMATCH, got {result['status']}"
    assert result["difference"] == -5000  # 20000 - 25000
    print("PASS test_tax_matcher_amount_mismatch")


def test_tax_matcher_duplicate_entry():
    """Two FEE_EXPENSE ledger entries for same settlement → DUPLICATE_ENTRY"""
    from app.services.financial_intelligence.tax_matcher import _match_component

    entry1 = MockLedgerEntry("LED-A", "FEE_EXPENSE", "SETL-9001", 56000)
    entry2 = MockLedgerEntry("LED-B", "FEE_EXPENSE", "SETL-9001", 56000)
    result = _match_component("SETL-9001", "FEE", 112000, [entry1, entry2])
    assert result["status"] == "DUPLICATE_ENTRY", f"Expected DUPLICATE_ENTRY, got {result['status']}"
    print("PASS test_tax_matcher_duplicate_entry")


# ============================================================================
# Unit tests for refund_matcher
# ============================================================================

def test_refund_matcher_matched():
    """Refund with matching ledger entry → REFUND_MATCHED"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-2A-001", "pay_ejcy127h6gmd47", "SETL-9001", 150000)
    ledger = [MockLedgerEntry("LED-015", "REFUND", "REF-2A-001", 150000)]
    result = _classify_refund(r, ledger)
    assert result["refund_status"] == "REFUND_MATCHED", f"Expected REFUND_MATCHED, got {result['refund_status']}"
    assert result["amount_difference"] == 0
    print("PASS test_refund_matcher_matched")


def test_refund_matcher_missing_in_ledger():
    """Refund processed but no ledger entry → REFUND_MISSING_IN_LEDGER"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-2A-025", "pay_7b1ijiys2n75bx", "SETL-9001", 44550)
    result = _classify_refund(r, [])  # No ledger entries
    assert result["refund_status"] == "REFUND_MISSING_IN_LEDGER", f"Got {result['refund_status']}"
    print("PASS test_refund_matcher_missing_in_ledger")


def test_refund_matcher_duplicate():
    """Same refund appears twice in ledger → DUPLICATE_REFUND"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-2A-020", "pay_ejcy127h6gmd47", "SETL-9001", 150000)
    ledger = [
        MockLedgerEntry("LED-015", "REFUND", "REF-2A-020", 150000),
        MockLedgerEntry("LED-031", "REFUND", "REF-2A-020", 150000),
    ]
    result = _classify_refund(r, ledger)
    assert result["refund_status"] == "DUPLICATE_REFUND", f"Got {result['refund_status']}"
    assert result["duplicate_count"] == 2
    print("PASS test_refund_matcher_duplicate")


def test_refund_matcher_amount_mismatch():
    """Ledger amount differs from gateway amount → REFUND_AMOUNT_MISMATCH"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-2A-023", "pay_w56fkps0dxme4p", "SETL-9003", 200000)  # Gateway: 200000
    ledger = [MockLedgerEntry("LED-034", "REFUND", "REF-2A-023", 141230)]      # Ledger: 141230
    result = _classify_refund(r, ledger)
    assert result["refund_status"] == "REFUND_AMOUNT_MISMATCH", f"Got {result['refund_status']}"
    assert result["amount_difference"] == -58770  # 141230 - 200000
    print("PASS test_refund_matcher_amount_mismatch")


def test_refund_matcher_pending():
    """Pending refund → REFUND_PENDING (no ledger check)"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-2A-011", "pay_qnezw9heyce4qg", None, 12220, "pending")
    result = _classify_refund(r, [])
    assert result["refund_status"] == "REFUND_PENDING", f"Got {result['refund_status']}"
    print("PASS test_refund_matcher_pending")


def test_refund_matcher_no_settlement_link():
    """Processed refund with no settlement_id → REFUND_SETTLEMENT_ADJUSTMENT_MISSING"""
    from app.services.financial_intelligence.refund_matcher import _classify_refund

    r = MockRefund("REF-X", "pay_abc", None, 50000, "processed")
    r.settlement_id = None  # explicitly no settlement
    result = _classify_refund(r, [])
    assert result["refund_status"] == "REFUND_SETTLEMENT_ADJUSTMENT_MISSING", f"Got {result['refund_status']}"
    print("PASS test_refund_matcher_no_settlement_link")


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    tests = [
        test_settlement_calculator_correct,
        test_settlement_calculator_discrepancy,
        test_settlement_calculator_refund_adjustment,
        test_settlement_calculator_zero_tax,
        test_tax_matcher_matched,
        test_tax_matcher_missing_ledger_entry,
        test_tax_matcher_zero_component_no_ledger,
        test_tax_matcher_amount_mismatch,
        test_tax_matcher_duplicate_entry,
        test_refund_matcher_matched,
        test_refund_matcher_missing_in_ledger,
        test_refund_matcher_duplicate,
        test_refund_matcher_amount_mismatch,
        test_refund_matcher_pending,
        test_refund_matcher_no_settlement_link,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Phase 2A Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL PHASE 2A TESTS PASSED")
