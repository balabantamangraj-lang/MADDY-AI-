"""
strategies/smc.py
-------------------
Smart Money Concepts — Phase 4 (in progress).

Yeh module abhi skeleton/stub state mein hai. Core function
signatures aur docstrings define kar diye gaye hain taaki agli
session mein seedha implementation pe focus kiya ja sake.
"""

import pandas as pd

import config


def detect_fair_value_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect bullish/bearish Fair Value Gaps (3-candle imbalance pattern).

    Bullish FVG: candle[i-1].High < candle[i+1].Low
        (gap between candle 1's high and candle 3's low)
    Bearish FVG: candle[i-1].Low > candle[i+1].High

    TODO (next session):
    - Rolling 3-candle window scan across df
    - Return DataFrame with columns: [date, type, gap_top, gap_bottom, midpoint]
    - midpoint = gap_bottom + FVG_MIDPOINT_RATIO * (gap_top - gap_bottom)
    """
    raise NotImplementedError("FVG detection — to be implemented in Phase 4.")


def fvg_entry_signal(df: pd.DataFrame, fvg_zones: pd.DataFrame) -> pd.Series:
    """
    Generate entry signals when price retraces to the 50% midpoint
    (Consequent Encroachment) of an unmitigated FVG.

    TODO (next session):
    - Track which FVG zones are still "open" (unmitigated)
    - Flag bars where price touches the midpoint of an open bullish FVG
    """
    raise NotImplementedError("FVG entry signal — to be implemented in Phase 4.")


def classify_gap(df: pd.DataFrame) -> pd.Series:
    """
    Classify each overnight gap as one of: 'common', 'breakaway', 'exhaustion', or None.

    TODO (next session):
    - Common: small gap, low volume, tends to fill quickly -> mean reversion strategy
    - Breakaway: gap out of a consolidation range, high volume -> gap & go momentum
    - Exhaustion: gap after an extended trend, often reverses -> fade strategy
    """
    raise NotImplementedError("Gap classification — to be implemented in Phase 4.")
