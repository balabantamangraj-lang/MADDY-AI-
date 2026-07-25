"""
data.py
--------
Market data fetch layer. Saara yfinance access yahin se hota hai,
taaki baaki modules ko yfinance ki quirks (multi-index columns,
Series ambiguity, rate limits) ke baare mein sochna na pade.
"""

import pandas as pd
import yfinance as yf
from functools import lru_cache


def fetch_ohlcv(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV data for a single ticker and return a clean, flat DataFrame.

    yfinance kabhi kabhi MultiIndex columns return karta hai (especially
    jab group_by='ticker' ho) — yahan hum use flatten karte hain taaki
    downstream code mein 'Close' column hamesha simple Series ho.
    """
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No data returned for {ticker}. Check ticker symbol or network access.")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index.name = "Date"
    return df


def fetch_universe(tickers: list[str], period: str = "2y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for a list of tickers. Returns {ticker: DataFrame}. Skips failures gracefully."""
    data = {}
    for ticker in tickers:
        try:
            data[ticker] = fetch_ohlcv(ticker, period=period, interval=interval)
        except Exception as e:
            print(f"[data.py] Warning: could not fetch {ticker} — {e}")
    return data


def get_close_series(df: pd.DataFrame) -> pd.Series:
    """
    Safely extract the Close price as a 1-D Series.

    Pandas kabhi kabhi 'Close' ko (n,1) DataFrame ke roop mein return
    karta hai jab underlying data multi-column ho — yeh helper isse
    hamesha flat Series mein convert karta hai (see: Phase 3 stability notes).
    """
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close
  
