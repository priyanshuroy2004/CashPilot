"""
Deterministic Multi-Factor Prioritization Engine for Financial Exceptions.

Evaluates:
  1. Financial Value at Risk (paise)
  2. Elapsed Age of the Issue (hours since financial event)
  3. Category Risk Weight (direct cash leakage vs operational lag)
  4. Operational Impact (customer disputes / chargeback probability)

Produces deterministic score (0-100) mapped to:
  CRITICAL : Score >= 70
  HIGH     : Score >= 50
  MEDIUM   : Score >= 30
  LOW      : Score < 30
"""

from typing import Tuple

# Financial thresholds in paise
VALUE_TIER_HIGH_PAISE = 2_000_000     # >= ₹20,000
VALUE_TIER_MID_PAISE = 500_000        # >= ₹5,000
VALUE_TIER_LOW_PAISE = 100_000        # >= ₹1,000

# Age thresholds in hours
AGE_TIER_OLD_HOURS = 120.0            # >= 5 days
AGE_TIER_MID_HOURS = 72.0             # >= 3 days
AGE_TIER_RECENT_HOURS = 24.0          # >= 1 day


def calculate_exception_priority(
    value_at_risk_paise: int,
    elapsed_hours: float,
    exception_type: str,
    has_customer_complaint: bool = False,
) -> Tuple[str, int]:
    """
    Computes deterministic risk level and score.
    Returns:
      (risk_level: str, score: int)
    """
    abs_val = abs(value_at_risk_paise)
    hours = max(0.0, float(elapsed_hours))
    
    # 1. Base Score from Value at Risk (0 to 45 points)
    if abs_val >= VALUE_TIER_HIGH_PAISE:
        value_score = 45
    elif abs_val >= VALUE_TIER_MID_PAISE:
        # Linear interpolation between 25 and 44
        fraction = (abs_val - VALUE_TIER_MID_PAISE) / (VALUE_TIER_HIGH_PAISE - VALUE_TIER_MID_PAISE)
        value_score = int(25 + fraction * 19)
    elif abs_val >= VALUE_TIER_LOW_PAISE:
        # Linear interpolation between 10 and 24
        fraction = (abs_val - VALUE_TIER_LOW_PAISE) / (VALUE_TIER_MID_PAISE - VALUE_TIER_LOW_PAISE)
        value_score = int(10 + fraction * 14)
    else:
        value_score = 5

    # 2. Age Component (0 to 30 points)
    if hours >= AGE_TIER_OLD_HOURS:
        age_score = 30
    elif hours >= AGE_TIER_MID_HOURS:
        fraction = (hours - AGE_TIER_MID_HOURS) / (AGE_TIER_OLD_HOURS - AGE_TIER_MID_HOURS)
        age_score = int(18 + fraction * 11)
    elif hours >= AGE_TIER_RECENT_HOURS:
        fraction = (hours - AGE_TIER_RECENT_HOURS) / (AGE_TIER_MID_HOURS - AGE_TIER_RECENT_HOURS)
        age_score = int(8 + fraction * 9)
    else:
        age_score = 3

    # 3. Category Weight multiplier
    # Cash leakage is highest risk; customer dispute risks follow
    category_weights = {
        "SETTLEMENT_MISSING_IN_BANK": 1.25,
        "SETTLEMENT_AMOUNT_MISMATCH": 1.20,
        "CALCULATION_DISCREPANCY": 1.15,
        "PAID_BUT_UNFULFILLED": 1.10,
        "PAYMENT_AMOUNT_MISMATCH": 1.10,
        "REFUND_MISSING_IN_LEDGER": 1.05,
        "PAYMENT_MISSING": 0.95,
        "FAILED_PAYMENT": 0.90,
    }
    weight = category_weights.get(exception_type, 1.0)

    raw_score = (value_score + age_score) * weight

    # 4. Support/Customer Escalation Signal (+15 bonus points)
    if has_customer_complaint:
        raw_score += 15

    score = min(100, max(0, int(round(raw_score))))

    # Deterministic mapping
    if score >= 70:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return level, score
