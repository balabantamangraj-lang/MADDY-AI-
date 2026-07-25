"""
config.py
----------
Central configuration for Maddy AI V5.0.
Sab constants aur tunable parameters yahan rakhe gaye hain,
taaki koi bhi module inhe import karke use kar sake — magic numbers
kahin scatter nahi honge.
"""

# ── Universe ──────────────────────────────────────────────────────
# Trade karne wale stocks (NSE tickers, yfinance format mein ".NS" suffix)
UNIVERSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
]

BENCHMARK = "^NSEI"  # Nifty 50 index — market regime filter aur CAPM ke liye

SECTOR_MAP = {
    "RELIANCE.NS": "Energy",
    "TCS.NS": "IT",
    "INFY.NS": "IT",
    "HDFCBANK.NS": "Banking",
    "SBIN.NS": "Banking",
}

# ── Capital & Risk Management (Phase 2) ──────────────────────────
INITIAL_CAPITAL = 1_000_000.0        # Starting capital (INR)
RISK_PER_TRADE_PCT = 0.01            # 1% risk per trade (ATR-based stop-loss)
MAX_CAPITAL_PER_STOCK_PCT = 0.20     # Max 20% capital allocation per stock
MAX_PORTFOLIO_HEAT_PCT = 0.05        # Max 5% total open risk at any time
MAX_SECTOR_EXPOSURE_PCT = 0.30       # Max 30% exposure to a single sector
CORRELATION_LOOKBACK_DAYS = 30       # Rolling window for correlation check
CORRELATION_THRESHOLD = 0.80         # Reject new trade if corr > this
KILL_SWITCH_EQUITY_PCT = 0.25        # Halt + liquidate if equity hits 25% of initial

# ── Entry Logic (Phase 1) ────────────────────────────────────────
EMA_TREND_PERIOD = 20                # Pullback EMA
EMA_REGIME_PERIOD = 50               # Market regime EMA (on benchmark)
ATR_PERIOD = 14
MIN_ENTRY_SCORE = 70                 # Minimum score threshold to take a trade

# ── Analytics (Phase 3) ───────────────────────────────────────────
RISK_FREE_RATE_ANNUAL = 0.07         # Approx. Indian risk-free rate (T-bill)
MONTE_CARLO_ITERATIONS = 1000
MONTE_CARLO_BLOCK_SIZE = 5

# ── Smart Money Concepts (Phase 4) ───────────────────────────────
FVG_MIDPOINT_RATIO = 0.5             # Consequent Encroachment level
