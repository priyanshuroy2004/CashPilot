"""
Dataset-type detector for CASHpilot AI CSV ingestion.

Identifies the type of an uploaded CSV (orders / payments / settlements /
settlement_lines / bank_transactions) from its column names by:

1. Normalising column names.
2. Trying each alias dictionary → computing required-column coverage.
3. Returning the type with the highest coverage (>= 40 % required threshold).

Filename is used only as a fallback hint, never as the primary signal.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.services.schema_normalizer.mapper import (
    DATASET_REQUIRED,
    _build_lookup,
    _normalise_key,
)

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _score_type(raw_columns: List[str], dataset_type: str) -> float:
    """
    Return fraction [0, 1] of required columns covered by *raw_columns*
    when mapped against *dataset_type*'s alias dictionary.
    """
    lookup = _build_lookup(dataset_type)
    required = DATASET_REQUIRED.get(dataset_type, [])
    if not required:
        return 0.0

    claimed: set[str] = set()
    for col in raw_columns:
        key = _normalise_key(col)
        canonical = lookup.get(key)
        if canonical:
            claimed.add(canonical)

    covered = sum(1 for r in required if r in claimed)
    return covered / len(required)


# ---------------------------------------------------------------------------
# Filename hints (weak signal — used only to break ties)
# ---------------------------------------------------------------------------
_FILENAME_HINTS: Dict[str, List[str]] = {
    "orders":            ["order", "sales", "purchase"],
    "payments":          ["payment", "transaction", "pay", "txn"],
    "settlements":       ["settlement", "settle", "payout"],
    "settlement_lines":  ["settlement_line", "setl_line", "line"],
    "bank_transactions": ["bank", "statement", "ledger", "account"],
}


def _filename_hint(filename: str) -> Optional[str]:
    stem = filename.lower().replace("_", "").replace("-", "").replace(" ", "")
    for dtype, hints in _FILENAME_HINTS.items():
        for h in hints:
            if h in stem:
                return dtype
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
ALL_TYPES = list(DATASET_REQUIRED.keys())

CONFIDENCE_THRESHOLD_HIGH   = 1.0   # all required cols covered
CONFIDENCE_THRESHOLD_MEDIUM = 0.6
CONFIDENCE_THRESHOLD_LOW    = 0.4   # minimum to attempt detection


def detect_type(
    raw_columns: List[str],
    filename: str = "",
) -> Tuple[str, float, str]:
    """
    Detect dataset type from column names.

    Returns
    -------
    (dataset_type, score, confidence)
        dataset_type : one of ALL_TYPES or "unknown"
        score        : coverage ratio [0, 1]
        confidence   : "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
    """
    scores: Dict[str, float] = {
        dtype: _score_type(raw_columns, dtype)
        for dtype in ALL_TYPES
    }

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    # If multiple types tie, use filename as tiebreaker
    top_score = best_score
    candidates = [t for t, s in scores.items() if abs(s - top_score) < 1e-6]
    if len(candidates) > 1:
        hint = _filename_hint(filename)
        if hint and hint in candidates:
            best_type = hint

    # Assign confidence tier
    if best_score >= CONFIDENCE_THRESHOLD_HIGH:
        confidence = "HIGH"
    elif best_score >= CONFIDENCE_THRESHOLD_MEDIUM:
        confidence = "MEDIUM"
    elif best_score >= CONFIDENCE_THRESHOLD_LOW:
        confidence = "LOW"
    else:
        best_type = "unknown"
        confidence = "UNKNOWN"

    return best_type, round(best_score, 3), confidence
