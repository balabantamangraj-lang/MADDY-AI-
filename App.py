"""
app.py
-------
Maddy AI V5.0 — Streamlit dashboard (entry point).
Sab modules (config, data, indicators, risk, scanner, backtest,
analytics) yahan se orchestrate hote hain.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd

import config
import data
import scanner
import backtest
import analytics

st.set_page_config(page_title="Maddy AI V5.0", layout="wide")

st.title("🧠 Maddy AI V5.0 — Quantitative Trading Engine")
st.caption("100% white-box algorithmic system · Smart Money Concepts · Institutional risk management")

tab_scanner, tab_backtest, tab_analytics = st.tabs(["📡 Live Scanner", "📊 Backtest", "📈 Analytics"])

# ── Sidebar controls ──────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    period = st.selectbox("Data period", ["1y", "2y", "5y"], index=1)
    min_score = st.slider("Min entry score", 0, 100, config.MIN_ENTRY_SCORE)
    run_button = st.button("🔄 Fetch & Refresh Data", use_container_width=True)

if "universe_data" not in st.session_state:
    st.session_state.universe_data = {}
    st.session_state.benchmark_df = None

if run_button or not st.session_state.universe_data:
    with st.spinner("Fetching market data..."):
        st.session_state.universe_data = data.fetch_universe(config.UNIVERSE, period=period)
        st.session_state.benchmark_df = data.fetch_ohlcv(config.BENCHMARK, period=period)

universe_data = st.session_state.universe_data
benchmark_df = st.session_state.benchmark_df

# ── Tab 1: Live Scanner ───────────────────────────────────────────
with tab_scanner:
    st.subheader("Universe Scan")
    if benchmark_df is not None and universe_data:
        signals_df = scanner.scan_universe(universe_data, benchmark_df, min_score=min_score)
        if signals_df.empty:
            st.info("No signals — check data fetch or lower the score threshold.")
        else:
            st.dataframe(signals_df, use_container_width=True)
            tradeable = signals_df[signals_df["tradeable"]]
            st.metric("Tradeable signals right now", len(tradeable))
    else:
        st.warning("Click 'Fetch & Refresh Data' in the sidebar to load the universe.")

# ── Tab 2: Backtest ───────────────────────────────────────────────
with tab_backtest:
    st.subheader("Strategy Backtest")
    if st.button("▶️ Run Backtest"):
        if benchmark_df is not None and universe_data:
            with st.spinner("Running backtest..."):
                result = backtest.run_backtest(universe_data, benchmark_df)
            st.session_state.backtest_result = result

    if "backtest_result" in st.session_state:
        result = st.session_state.backtest_result
        equity_curve = result["equity_curve"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Final Equity", f"₹{equity_curve.iloc[-1]:,.0f}")
        total_return = (equity_curve.iloc[-1] / config.INITIAL_CAPITAL - 1) * 100
        col2.metric("Total Return", f"{total_return:.1f}%")
        col3.metric("Total Trades", len(result["trade_log"]))

        st.line_chart(equity_curve)

        with st.expander("Trade Log"):
            st.dataframe(pd.DataFrame(result["trade_log"]), use_container_width=True)

# ── Tab 3: Analytics ──────────────────────────────────────────────
with tab_analytics:
    st.subheader("Performance Analytics")
    if "backtest_result" in st.session_state:
        result = st.session_state.backtest_result
        equity_curve = result["equity_curve"]
        strategy_returns = equity_curve.pct_change().dropna()
        benchmark_returns = data.get_close_series(benchmark_df).pct_change().dropna()

        capm = analytics.calculate_capm(strategy_returns, benchmark_returns)
        col1, col2 = st.columns(2)
        col1.metric("Alpha (annualized)", f"{capm['alpha']:.2%}" if pd.notna(capm["alpha"]) else "N/A")
        col2.metric("Beta", f"{capm['beta']:.2f}" if pd.notna(capm["beta"]) else "N/A")

        if st.button("🎲 Run Monte Carlo Simulation"):
            with st.spinner(f"Running {config.MONTE_CARLO_ITERATIONS} block-bootstrap iterations..."):
                mc = analytics.monte_carlo_block_bootstrap(strategy_returns)
            c1, c2, c3 = st.columns(3)
            c1.metric("Risk of Ruin", f"{mc['risk_of_ruin_pct']:.1f}%")
            c2.metric("Median Max Drawdown", f"{mc['median_max_drawdown_pct']:.1f}%")
            c3.metric("5th Percentile Equity", f"₹{mc['pessimistic_5th_percentile_equity']:,.0f}")
    else:
        st.info("Run a backtest first (Backtest tab) to see analytics.")
