"""
risk.py
--------
Institutional-grade risk management (Phase 2).
Har trade yahan se guzarta hai before execution — position sizing,
portfolio heat, sector limits, correlation shield, aur kill switch
sab yahin enforce hote hain.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field

import config


@dataclass
class Position:
    ticker: str
    sector: str
    entry_price: float
    stop_loss: float
    shares: int
    risk_amount: float  # capital at risk on this position (in currency)


@dataclass
class Portfolio:
    equity: float = config.INITIAL_CAPITAL
    initial_capital: float = config.INITIAL_CAPITAL
    positions: dict[str, Position] = field(default_factory=dict)
    halted: bool = False

    @property
    def total_open_risk(self) -> float:
        return sum(p.risk_amount for p in self.positions.values())

    @property
    def open_risk_pct(self) -> float:
        return self.total_open_risk / self.equity if self.equity > 0 else 0.0

    @property
    def sector_exposure(self) -> dict[str, float]:
        """Capital allocated per sector, as % of equity."""
        exposure: dict[str, float] = {}
        for p in self.positions.values():
            allocated = p.shares * p.entry_price
            exposure[p.sector] = exposure.get(p.sector, 0.0) + allocated
        return {sector: amt / self.equity for sector, amt in exposure.items()} if self.equity > 0 else {}


def calculate_position_size(
    equity: float,
    entry_price: float,
    stop_loss_price: float,
    risk_pct: float = config.RISK_PER_TRADE_PCT,
    max_capital_pct: float = config.MAX_CAPITAL_PER_STOCK_PCT,
) -> tuple[int, float]:
    """
    ATR-based position sizing: risk exactly `risk_pct` of equity on
    this trade, bounded by the max-capital-per-stock cap.

    Returns (shares, risk_amount).
    """
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share <= 0:
        return 0, 0.0

    risk_budget = equity * risk_pct
    shares_by_risk = int(risk_budget / risk_per_share)

    max_capital = equity * max_capital_pct
    shares_by_capital = int(max_capital / entry_price) if entry_price > 0 else 0

    shares = max(0, min(shares_by_risk, shares_by_capital))
    risk_amount = shares * risk_per_share
    return shares, risk_amount


def check_portfolio_heat(portfolio: Portfolio, new_risk_amount: float) -> bool:
    """True if adding new_risk_amount keeps total open risk within MAX_PORTFOLIO_HEAT_PCT."""
    projected = portfolio.total_open_risk + new_risk_amount
    return (projected / portfolio.equity) <= config.MAX_PORTFOLIO_HEAT_PCT


def check_sector_limit(portfolio: Portfolio, sector: str, new_allocation: float) -> bool:
    """True if adding new_allocation to `sector` stays within MAX_SECTOR_EXPOSURE_PCT."""
    current = portfolio.sector_exposure.get(sector, 0.0) * portfolio.equity
    projected_pct = (current + new_allocation) / portfolio.equity
    return projected_pct <= config.MAX_SECTOR_EXPOSURE_PCT


def check_correlation_shield(
    candidate_returns: pd.Series,
    open_position_returns: dict[str, pd.Series],
    lookback: int = config.CORRELATION_LOOKBACK_DAYS,
    threshold: float = config.CORRELATION_THRESHOLD,
) -> bool:
    """
    Anti-Correlation Shield: True (trade allowed) if candidate's
    correlation with EVERY open position is <= threshold over the
    rolling lookback window. False = reject the new trade.
    """
    if not open_position_returns:
        return True

    candidate_recent = candidate_returns.tail(lookback)

    for ticker, existing_returns in open_position_returns.items():
        existing_recent = existing_returns.tail(lookback)
        aligned = pd.concat([candidate_recent, existing_recent], axis=1).dropna()
        if len(aligned) < 2:
            continue
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if corr is not None and abs(corr) > threshold:
            return False

    return True


def check_kill_switch(portfolio: Portfolio) -> bool:
    """
    System Kill Switch (Ruin Protection): returns True if equity has
    dropped to or below KILL_SWITCH_EQUITY_PCT of initial capital.
    Caller should force-liquidate and halt trading if True.
    """
    threshold_equity = portfolio.initial_capital * config.KILL_SWITCH_EQUITY_PCT
    breached = portfolio.equity <= threshold_equity
    if breached:
        portfolio.halted = True
    return breached


def validate_new_trade(
    portfolio: Portfolio,
    ticker: str,
    sector: str,
    entry_price: float,
    stop_loss_price: float,
    candidate_returns: pd.Series,
    open_position_returns: dict[str, pd.Series],
) -> dict:
    """
    Runs a candidate trade through the FULL risk gauntlet:
    kill switch -> position sizing -> portfolio heat -> sector limit
    -> correlation shield. Returns a dict with the verdict and sizing.
    """
    if portfolio.halted or check_kill_switch(portfolio):
        return {"approved": False, "reason": "Kill switch active — trading halted."}

    shares, risk_amount = calculate_position_size(portfolio.equity, entry_price, stop_loss_price)
    if shares <= 0:
        return {"approved": False, "reason": "Position size computed to zero (check ATR/stop distance)."}

    if not check_portfolio_heat(portfolio, risk_amount):
        return {"approved": False, "reason": f"Portfolio heat limit ({config.MAX_PORTFOLIO_HEAT_PCT:.0%}) breached."}

    allocation = shares * entry_price
    if not check_sector_limit(portfolio, sector, allocation):
        return {"approved": False, "reason": f"Sector exposure limit ({config.MAX_SECTOR_EXPOSURE_PCT:.0%}) breached for {sector}."}

    if not check_correlation_shield(candidate_returns, open_position_returns):
        return {"approved": False, "reason": f"Correlation shield: exceeds {config.CORRELATION_THRESHOLD} with an open position."}

    return {
        "approved": True,
        "shares": shares,
        "risk_amount": risk_amount,
        "allocation": allocation,
    }
  
