"""
scanner.py
-----------
Universe scanner: har stock ko regime filter + entry score ke
through pass karke, tradeable signals ki list banata hai.
"""

import pandas as pd

import config
import data
import indicators


def scan_universe(
    universe_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame,
    min_score: float = config.MIN_ENTRY_SCORE,
) -> pd.DataFrame:
    """
    Scan the full universe and return a DataFrame of the latest
    signal per ticker: score, regime alignment, ATR, suggested stop.

    Only rows where regime is bullish AND score >= min_score are
    flagged as `tradeable = True`.
    """
    regime = indicators.market_regime(benchmark_df, config.EMA_REGIME_PERIOD)
    bullish_regime_now = bool(regime.iloc[-1]) if len(regime) else False

    rows = []
    for ticker, df in universe_data.items():
        if df is None or df.empty or len(df) < max(config.EMA_TREND_PERIOD, config.ATR_PERIOD) + 5:
            continue

        score_series = indicators.entry_score(df, config.EMA_TREND_PERIOD, config.ATR_PERIOD)
        atr_series = indicators.atr(df, config.ATR_PERIOD)

        latest_close = float(data.get_close_series(df).iloc[-1])
        latest_score = float(score_series.iloc[-1])
        latest_atr = float(atr_series.iloc[-1])
        suggested_stop = latest_close - (2 * latest_atr)  # 2x ATR stop, tunable

        tradeable = bullish_regime_now and (latest_score >= min_score)

        rows.append(
            {
                "ticker": ticker,
                "sector": config.SECTOR_MAP.get(ticker, "Unknown"),
                "close": latest_close,
                "entry_score": round(latest_score, 1),
                "atr": round(latest_atr, 2),
                "suggested_stop": round(suggested_stop, 2),
                "regime_bullish": bullish_regime_now,
                "tradeable": tradeable,
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("entry_score", ascending=False).reset_index(drop=True)
    return result
  
