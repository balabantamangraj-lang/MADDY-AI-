"""
analytics.py
-------------
Advanced quant analytics (Phase 3): CAPM Alpha/Beta aur Monte Carlo
block-bootstrap simulation for risk-of-ruin analysis.
"""

import numpy as np
import pandas as pd

import config


def calculate_capm(strategy_returns: pd.Series, benchmark_returns: pd.Series, risk_free_annual: float = config.RISK_FREE_RATE_ANNUAL) -> dict:
    """
    CAPM regression: strategy_returns ~ alpha + beta * benchmark_returns.

    Beta = volatility/sensitivity vs Nifty.
    Alpha (annualized) = risk-adjusted outperformance vs Nifty.
    """
    aligned = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
    aligned.columns = ["strategy", "benchmark"]

    if len(aligned) < 2:
        return {"alpha": np.nan, "beta": np.nan}

    daily_rf = risk_free_annual / 252
    excess_strategy = aligned["strategy"] - daily_rf
    excess_benchmark = aligned["benchmark"] - daily_rf

    covariance = np.cov(excess_strategy, excess_benchmark)[0, 1]
    variance = np.var(excess_benchmark)
    beta = covariance / variance if variance != 0 else np.nan

    alpha_daily = excess_strategy.mean() - beta * excess_benchmark.mean()
    alpha_annualized = alpha_daily * 252

    return {"alpha": float(alpha_annualized), "beta": float(beta)}


def monte_carlo_block_bootstrap(
    daily_returns: pd.Series,
    initial_capital: float = config.INITIAL_CAPITAL,
    iterations: int = config.MONTE_CARLO_ITERATIONS,
    block_size: int = config.MONTE_CARLO_BLOCK_SIZE,
    ruin_threshold_pct: float = config.KILL_SWITCH_EQUITY_PCT,
) -> dict:
    """
    Block-bootstrap Monte Carlo simulation.

    Resamples historical daily returns in contiguous blocks (preserves
    short-term autocorrelation/volatility clustering better than i.i.d.
    resampling) to project equity paths.

    Returns: risk_of_ruin (%), median_max_drawdown (%),
    pessimistic_5th_percentile_equity.
    """
    returns = daily_returns.dropna().values
    n = len(returns)
    if n < block_size:
        raise ValueError("Not enough return history for the given block_size.")

    horizon = n  # simulate forward for the same number of days as history
    n_blocks = int(np.ceil(horizon / block_size))

    final_equities = []
    max_drawdowns = []
    ruin_count = 0
    ruin_equity = initial_capital * ruin_threshold_pct

    rng = np.random.default_rng()

    for _ in range(iterations):
        path_returns = []
        for _ in range(n_blocks):
            start_idx = rng.integers(0, n - block_size + 1)
            path_returns.extend(returns[start_idx:start_idx + block_size])
        path_returns = np.array(path_returns[:horizon])

        equity_path = initial_capital * np.cumprod(1 + path_returns)
        equity_path = np.insert(equity_path, 0, initial_capital)

        running_max = np.maximum.accumulate(equity_path)
        drawdown = (equity_path - running_max) / running_max
        max_dd = drawdown.min()  # most negative value

        final_equities.append(equity_path[-1])
        max_drawdowns.append(abs(max_dd))

        if equity_path.min() <= ruin_equity:
            ruin_count += 1

    final_equities = np.array(final_equities)
    max_drawdowns = np.array(max_drawdowns)

    return {
        "risk_of_ruin_pct": (ruin_count / iterations) * 100,
        "median_max_drawdown_pct": float(np.median(max_drawdowns) * 100),
        "pessimistic_5th_percentile_equity": float(np.percentile(final_equities, 5)),
        "median_final_equity": float(np.median(final_equities)),
    }
  
