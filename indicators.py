"""
indicators.py
--------------
Pure-math technical indicators. Koi black-box ML nahi — sirf
statistics aur price-action based calculations (white-box philosophy).
"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range — volatility measure used for stop-loss
    distance and position sizing.
    """
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(span=period, adjust=False).mean()


def market_regime(benchmark_df: pd.DataFrame, ema_period: int = 50) -> pd.Series:
    """
    Market Regime Filter (Phase 1): returns a boolean Series —
    True = bullish regime (benchmark close > its EMA), False = bearish.
    Trades sirf regime ki direction mein allowed hain.
    """
    close = benchmark_df["Close"]
    trend_ema = ema(close, ema_period)
    return close > trend_ema


def entry_score(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 14) -> pd.Series:
    """
    Composite entry score (0-100) for the 20 EMA pullback strategy.

    Yeh ek starter scoring model hai — trend alignment, pullback
    proximity to EMA, aur volatility-normalized momentum ko combine
    karta hai. MIN_ENTRY_SCORE (config.py) se compare karke trade
    liya jaata hai.

    NOTE: Yeh weights tunable hain — abhi ek reasonable default diya
    gaya hai jise backtest ke through refine kiya ja sakta hai.
    """
    close = df["Close"]
    trend_ema = ema(close, ema_period)
    atr_series = atr(df, atr_period)

    # 1. Trend alignment: price above EMA = bullish component
    trend_component = np.where(close > trend_ema, 40, 0)

    # 2. Pullback proximity: closer price is to EMA (within 1 ATR), higher score
    distance_in_atr = (close - trend_ema).abs() / atr_series.replace(0, np.nan)
    proximity_component = np.clip(40 * (1 - distance_in_atr), 0, 40)
    proximity_component = proximity_component.fillna(0)

    # 3. Momentum: rate of change over last 5 bars, normalized
    roc = close.pct_change(5)
    momentum_component = np.clip(20 * (roc / roc.rolling(50).std().replace(0, np.nan)).fillna(0), -20, 20)
    momentum_component = momentum_component.clip(lower=0)  # only reward positive momentum

    score = trend_component + proximity_component + momentum_component
    return pd.Series(score, index=df.index, name="entry_score").clip(0, 100)
