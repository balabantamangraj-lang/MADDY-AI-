"""
backtest.py
------------
Backtesting engine: historical data pe strategy + risk module ko
bar-by-bar simulate karta hai aur equity curve / trade log return karta hai.
"""

import pandas as pd

import config
import data
import indicators
from risk import Portfolio, validate_new_trade, Position


def run_backtest(
    universe_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame,
    initial_capital: float = config.INITIAL_CAPITAL,
) -> dict:
    """
    Bar-by-bar backtest across the universe.

    NOTE: Yeh ek skeleton implementation hai — core loop structure
    yahan set kar diya gaya hai (regime check -> score -> risk gate
    -> position tracking -> exits). Exit logic (e.g. trailing stop,
    target, time-stop) ko refine karna Phase 4/5 mein continue karenge.

    Returns dict with: equity_curve (pd.Series), trade_log (list[dict]).
    """
    portfolio = Portfolio(equity=initial_capital, initial_capital=initial_capital)
    regime = indicators.market_regime(benchmark_df, config.EMA_REGIME_PERIOD)

    # Precompute closes/returns for correlation shield
    closes = {t: data.get_close_series(df) for t, df in universe_data.items()}
    returns = {t: c.pct_change() for t, c in closes.items()}

    # Precompute indicators per ticker
    scores = {t: indicators.entry_score(df, config.EMA_TREND_PERIOD, config.ATR_PERIOD) for t, df in universe_data.items()}
    atrs = {t: indicators.atr(df, config.ATR_PERIOD) for t, df in universe_data.items()}

    equity_curve = []
    trade_log = []

    common_dates = benchmark_df.index

    for date in common_dates:
        if portfolio.halted:
            equity_curve.append({"date": date, "equity": portfolio.equity})
            continue

        is_bullish = bool(regime.loc[date]) if date in regime.index else False

        if is_bullish:
            for ticker, df in universe_data.items():
                if ticker in portfolio.positions:
                    continue  # already holding
                if date not in scores[ticker].index:
                    continue

                score = scores[ticker].loc[date]
                if pd.isna(score) or score < config.MIN_ENTRY_SCORE:
                    continue

                entry_price = float(closes[ticker].loc[date])
                atr_val = atrs[ticker].loc[date]
                if pd.isna(atr_val):
                    continue
                stop_loss = entry_price - (2 * float(atr_val))

                open_returns = {
                    t: returns[t].loc[:date] for t in portfolio.positions.keys()
                }
                candidate_returns = returns[ticker].loc[:date]

                verdict = validate_new_trade(
                    portfolio,
                    ticker=ticker,
                    sector=config.SECTOR_MAP.get(ticker, "Unknown"),
                    entry_price=entry_price,
                    stop_loss_price=stop_loss,
                    candidate_returns=candidate_returns,
                    open_position_returns=open_returns,
                )

                if verdict["approved"]:
                    portfolio.positions[ticker] = Position(
                        ticker=ticker,
                        sector=config.SECTOR_MAP.get(ticker, "Unknown"),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        shares=verdict["shares"],
                        risk_amount=verdict["risk_amount"],
                    )
                    trade_log.append({"date": date, "ticker": ticker, "action": "BUY", "price": entry_price, "shares": verdict["shares"]})

        # Check exits (stop-loss hit) for open positions
        for ticker in list(portfolio.positions.keys()):
            if date not in closes[ticker].index:
                continue
            current_price = float(closes[ticker].loc[date])
            pos = portfolio.positions[ticker]
            if current_price <= pos.stop_loss:
                pnl = (current_price - pos.entry_price) * pos.shares
                portfolio.equity += pnl
                trade_log.append({"date": date, "ticker": ticker, "action": "SELL_STOP", "price": current_price, "pnl": pnl})
                del portfolio.positions[ticker]

        # Kill switch check
        from risk import check_kill_switch
        if check_kill_switch(portfolio):
            # Force liquidate everything
            for ticker, pos in list(portfolio.positions.items()):
                if date in closes[ticker].index:
                    current_price = float(closes[ticker].loc[date])
                    pnl = (current_price - pos.entry_price) * pos.shares
                    portfolio.equity += pnl
                    trade_log.append({"date": date, "ticker": ticker, "action": "SELL_KILLSWITCH", "price": current_price, "pnl": pnl})
            portfolio.positions.clear()

        equity_curve.append({"date": date, "equity": portfolio.equity})

    equity_df = pd.DataFrame(equity_curve).set_index("date")["equity"]
    return {"equity_curve": equity_df, "trade_log": trade_log, "final_portfolio": portfolio}
    
