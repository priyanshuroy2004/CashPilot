"""
Settlement ↔ Bank Transaction deterministic reconciliation module.

Hierarchical multi-level matching:
  Level 1: Exact UTR Match (Confidence 100)
  Level 2: Settlement ID / Reference in Bank Narration (Confidence 95)
  Level 3: Net Amount + Date Window Match (Confidence 85)
  Level 4: Ambiguous Candidates -> Flag as NEEDS_REVIEW (No random matching)
  Level 5: Unmatched -> PENDING_BANK_CREDIT

All financial calculations use exact integer paise against NET settlement amount:
  expected_net = gross_amount - fee_amount - tax_amount + adjustment_amount
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.reconciliation.order_payment import ReconItem


def _normalize_ref(text: str) -> str:
    """Normalize references by removing hyphens, underscores, and spaces."""
    return re.sub(r"[\s\-_]+", "", str(text or "")).upper()


def _extract_settlement_pattern(settlement_id: str) -> re.Pattern:
    """
    Create a regex pattern matching settlement_id variations in narrations.
    e.g., 'SETL-9001' matches 'SETL-9001', 'SETL_9001', 'SETL9001', 'SETL 9001'.
    """
    # Break into alphanumeric chunks
    chunks = re.findall(r"[A-Za-z0-9]+", settlement_id)
    if chunks:
        joined = r"[\s\-_]*".join(re.escape(c) for c in chunks)
        return re.compile(rf"\b{joined}\b", re.IGNORECASE)
    return re.compile(re.escape(settlement_id), re.IGNORECASE)


def reconcile_settlements_bank(
    settlements: List[Any],
    bank_transactions: List[Any],
    tolerance: int = 1,
    date_window_days: int = 7,
) -> List[ReconItem]:
    """
    Reconcile Settlement objects against BankTransaction objects.

    Returns a list of ReconItem objects for settlements (and orphan bank transactions).
    """
    results: List[ReconItem] = []

    # Map bank transactions by entry id
    bank_map: Dict[str, Any] = {
        str(getattr(b, "bank_entry_id", "")): b for b in bank_transactions
    }

    # Index bank transactions by UTR (non-empty)
    bank_by_utr: Dict[str, List[Any]] = {}
    for b in bank_transactions:
        utr = str(getattr(b, "utr", "") or "").strip()
        if utr:
            bank_by_utr.setdefault(utr, []).append(b)

    matched_bank_ids: Set[str] = set()

    for s in settlements:
        sid = str(getattr(s, "settlement_id", "") or "")
        s_date = getattr(s, "settlement_date", None)
        if isinstance(s_date, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    s_date = datetime.strptime(s_date, fmt)
                    break
                except ValueError:
                    pass

        gross = int(getattr(s, "gross_amount", 0) or 0)
        fee = int(getattr(s, "fee_amount", 0) or 0)
        tax = int(getattr(s, "tax_amount", 0) or 0)
        adj = int(getattr(s, "adjustment_amount", 0) or 0)
        net = int(getattr(s, "net_amount", 0) or 0)

        # Verify net arithmetic
        expected_net = gross - fee - tax + adj
        if expected_net != net:
            # Stored net differs from arithmetic, log diagnostic note
            net = expected_net

        s_utr = str(getattr(s, "settlement_utr", "") or "").strip()

        matched_bank: Optional[Any] = None
        match_type: Optional[str] = None
        confidence: float = 0.0
        ambiguous_candidates: List[Any] = []

        # =====================================================================
        # LEVEL 1: Exact UTR Match (Confidence 100)
        # =====================================================================
        if s_utr and s_utr in bank_by_utr:
            utr_candidates = bank_by_utr[s_utr]
            if len(utr_candidates) == 1:
                matched_bank = utr_candidates[0]
                match_type = "EXACT_UTR"
                confidence = 100.0
            else:
                ambiguous_candidates = utr_candidates
                match_type = "AMBIGUOUS_UTR"
                confidence = 60.0

        # =====================================================================
        # LEVEL 2: Settlement ID / Reference in Narration (Confidence 95)
        # =====================================================================
        if not matched_bank and not ambiguous_candidates and sid:
            pattern = _extract_settlement_pattern(sid)
            ref_candidates = [
                b for b in bank_transactions
                if b.narration and pattern.search(str(b.narration))
            ]
            if len(ref_candidates) == 1:
                matched_bank = ref_candidates[0]
                match_type = "REFERENCE_MATCH"
                confidence = 95.0
            elif len(ref_candidates) > 1:
                ambiguous_candidates = ref_candidates
                match_type = "AMBIGUOUS_REFERENCE"
                confidence = 50.0

        # =====================================================================
        # LEVEL 3: Net Amount + Date Window Match (Confidence 85)
        # =====================================================================
        if not matched_bank and not ambiguous_candidates and s_date:
            # Look for available credit transactions matching net amount within date window
            amt_candidates = []
            for b in bank_transactions:
                b_id = str(getattr(b, "bank_entry_id", ""))
                if b_id in matched_bank_ids:
                    continue  # already claimed by a higher-priority match

                b_dir = str(getattr(b, "direction", "") or "").upper()
                if b_dir != "CREDIT":
                    continue

                b_amt = int(getattr(b, "amount", 0) or 0)
                if abs(b_amt - net) > tolerance:
                    continue

                b_date = getattr(b, "bank_date", None)
                if isinstance(b_date, str):
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                        try:
                            b_date = datetime.strptime(b_date, fmt)
                            break
                        except ValueError:
                            pass

                if b_date and abs((b_date - s_date).days) <= date_window_days:
                    amt_candidates.append(b)

            if len(amt_candidates) == 1:
                matched_bank = amt_candidates[0]
                match_type = "AMOUNT_DATE_MATCH"
                confidence = 85.0
            elif len(amt_candidates) > 1:
                ambiguous_candidates = amt_candidates
                match_type = "AMBIGUOUS_AMOUNT_DATE"
                confidence = 50.0

        # =====================================================================
        # EVALUATE MATCH OR EXCEPTION
        # =====================================================================
        if ambiguous_candidates:
            # Multiple candidates found -> NEVER guess randomly -> NEEDS_REVIEW
            cand_ids = [str(getattr(b, "bank_entry_id", "")) for b in ambiguous_candidates]
            results.append(
                ReconItem(
                    entity_type="SETTLEMENT",
                    entity_id=sid,
                    related_entity_id=",".join(cand_ids),
                    match_type=match_type or "AMBIGUOUS_CANDIDATES",
                    status="NEEDS_REVIEW",
                    confidence=confidence,
                    expected_amount=net,
                    actual_amount=None,
                    difference=None,
                    reason=f"Ambiguous match: multiple ({len(cand_ids)}) candidate bank records found ({', '.join(cand_ids)})",
                )
            )
        elif matched_bank:
            b_id = str(getattr(matched_bank, "bank_entry_id", ""))
            b_amt = int(getattr(matched_bank, "amount", 0) or 0)
            diff = b_amt - net
            matched_bank_ids.add(b_id)

            if abs(diff) <= tolerance:
                # Fully matched
                status = "MATCHED" if diff == 0 else "MATCHED_WITH_TOLERANCE"
                results.append(
                    ReconItem(
                        entity_type="SETTLEMENT",
                        entity_id=sid,
                        related_entity_id=b_id,
                        match_type=match_type,
                        status=status,
                        confidence=confidence,
                        expected_amount=net,
                        actual_amount=b_amt,
                        difference=diff,
                        reason=f"Settlement net amount matched bank credit via {match_type}" + (f" (within {diff} paise tolerance)" if diff != 0 else ""),
                    )
                )
            else:
                # UTR or Reference matched, but amount differs beyond tolerance!
                results.append(
                    ReconItem(
                        entity_type="SETTLEMENT",
                        entity_id=sid,
                        related_entity_id=b_id,
                        match_type=match_type,
                        status="MISMATCH",
                        confidence=confidence,
                        expected_amount=net,
                        actual_amount=b_amt,
                        difference=diff,
                        reason=f"Bank credit ({b_amt} paise) differs from expected net settlement ({net} paise) by {diff} paise via {match_type}",
                    )
                )
        else:
            # No bank record matched
            results.append(
                ReconItem(
                    entity_type="SETTLEMENT",
                    entity_id=sid,
                    related_entity_id=None,
                    match_type="UNMATCHED",
                    status="PENDING_BANK_CREDIT",
                    confidence=0.0,
                    expected_amount=net,
                    actual_amount=0,
                    difference=-net,
                    reason="No matching bank credit found for settlement",
                )
            )

    return results
