import pandas as pd, numpy as np, yfinance as yf
from datetime import datetime
import itertools
import warnings
warnings.filterwarnings('ignore') # To keep terminal clean from yfinance warnings

# --- 1. CONFIGURATION & UNIVERSE ---
INITIAL_CAPITAL = 100000
MAX_PORTFOLIO_HEAT = 0.05
MAX_SECTOR_EXPOSURE = 0.30
COMMISSION = 0.0005
SLIPPAGE = 0.001
RUIN_THRESHOLD = 0.25 # 25% Equity left = System Halt
RF_RATE = 0.06 # 6% Risk Free Rate

WATCHLIST = {
    "RELIANCE.NS": "ENERGY", 
    "TCS.NS": "IT", 
    "INFY.NS": "IT", 
    "HDFCBANK.NS": "BANKING", 
    "SBIN.NS": "BANKING"
}

# --- 2. INDICATORS & REGIME ---
def add_indicators(df):
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    return df

def get_nifty_regime(nifty_hist):
    if len(nifty_hist) < 50: return {"is_bullish": False}
    ema50 = nifty_hist['Close'].ewm(span=50, adjust=False).mean()
    return {"is_bullish": nifty_hist['Close'].iloc[-1] > ema50.iloc[-1]}

def evaluate_entry(symbol, sector, hist, equity, open_trades, regime):
    score = 80 if hist['Close'].iloc[-1] > hist['EMA20'].iloc[-1] and regime['is_bullish'] else 40
    if score >= 70: 
        return {"status": "READY", "score": score}
    return {"status": "REJECT"}

# --- 3. MULTI-ASSET PORTFOLIO ENGINE ---
def run_portfolio_backtest(data_dict, nifty_df, timeline, sl_mult=2.0, tp_mult=4.0):
    if len(timeline) == 0: return {}
    
    portfolio = {"cash": INITIAL_CAPITAL, "equity": INITIAL_CAPITAL, "positions": {}, "trades": [], "daily_log": [], "ledger": []}
    pending_signals = []
    stop_trading = False
    
    peak_equity = INITIAL_CAPITAL
    nifty_shares = INITIAL_CAPITAL / float(np.squeeze(nifty_df['Close'].iloc[0])) if not nifty_df.empty else 0
    
    nifty_peak = INITIAL_CAPITAL
    
    for i, date in enumerate(timeline):
        if i < 250: continue # Global Warmup Check
        
        # Kill-Switch & Liquidation
        if portfolio["equity"] < INITIAL_CAPITAL * RUIN_THRESHOLD:
            if not stop_trading:
                portfolio["ledger"].append({"date": date, "action": "SYSTEM_HALTED", "reason": "Equity dropped below 25%"})
                stop_trading = True
                for sym, pos in list(portfolio["positions"].items()):
                    exit_p = data_dict[sym].loc[date, 'Open'] * (1 - SLIPPAGE) if date in data_dict[sym].index else pos['entry'] * 0.7
                    sell_val = exit_p * pos['qty']
                    sell_comm = sell_val * COMMISSION
                    net_pnl = sell_val - sell_comm - pos['buy_value'] - pos['buy_comm']
                    
                    portfolio["cash"] += (sell_val - sell_comm)
                    portfolio["trades"].append({"symbol": sym, "entry_date": pos['date'], "exit_date": date, "entry": pos['entry'], "exit": exit_p, "qty": pos['qty'], "pnl": net_pnl})
                    portfolio["ledger"].append({"date": date, "action": "FORCED_LIQUIDATION_HALT", "symbol": sym, "price": exit_p, "pnl": net_pnl})
                portfolio["positions"].clear()
                portfolio["equity"] = portfolio["cash"]
            continue

        nifty_hist = nifty_df[nifty_df.index <= date]
        regime = {"is_bullish": False} if nifty_hist.empty else get_nifty_regime(nifty_hist)

        # Process Exits
        closed_symbols = []
        for sym, pos in list(portfolio["positions"].items()):
            if date not in data_dict[sym].index:
                pos['missing_days'] = pos.get('missing_days', 0) + 1
                if pos['missing_days'] > 5:
                    last_close = data_dict[sym]['Close'].iloc[-1] if not data_dict[sym].empty else pos['entry']
                    closed_symbols.append((sym, last_close * 0.7, "FORCED_EXIT_DELISTED"))
                continue
            else:
                pos['missing_days'] = 0

            hist = data_dict[sym].loc[:date]
            open_p, high, low = hist['Open'].iloc[-1], hist['High'].iloc[-1], hist['Low'].iloc[-1]
            
            if low <= pos['sl']:
                closed_symbols.append((sym, min(open_p, pos['sl']) * (1 - SLIPPAGE), "SELL_SL_HIT"))
            elif high >= pos['target']:
                closed_symbols.append((sym, max(open_p, pos['target']) * (1 - SLIPPAGE), "SELL_TP_HIT"))

        for sym, exit_p, reason in closed_symbols:
            pos = portfolio["positions"][sym]
            sell_val = exit_p * pos['qty']
            sell_comm = sell_val * COMMISSION
            net_pnl = sell_val - sell_comm - pos['buy_value'] - pos['buy_comm']
            
            portfolio["cash"] += (sell_val - sell_comm)
            portfolio["trades"].append({"symbol": sym, "entry_date": pos['date'], "exit_date": date, "entry": pos['entry'], "exit": exit_p, "qty": pos['qty'], "pnl": net_pnl})
            portfolio["ledger"].append({"date": date, "action": reason, "symbol": sym, "price": exit_p, "pnl": net_pnl})
            del portfolio["positions"][sym]

        # Execute Pending Signals
        pending_signals.sort(key=lambda x: x['score'], reverse=True)
        for sig in pending_signals:
            if (pd.to_datetime(date) - pd.to_datetime(sig['signal_date'])).days > 4: 
                continue # Stale signal expiry
                
            sym = sig['symbol']
            if sym in portfolio["positions"] or date not in data_dict[sym].index: 
                continue
                
            actual_entry = data_dict[sym].loc[date, 'Open'] * (1 + SLIPPAGE)
            actual_sl = actual_entry - (sl_mult * sig['atr'])
            actual_target = actual_entry + (tp_mult * sig['atr'])
            risk = actual_entry - actual_sl
            
            if risk <= 0: continue
            
            # Position Sizing
            raw_qty = int((portfolio["equity"] * 0.01) / risk)
            max_pos_qty = int((portfolio["equity"] * 0.20) / actual_entry)
            qty = min(raw_qty, max_pos_qty)
            
            trade_val = qty * actual_entry
            buy_comm = trade_val * COMMISSION
            total_entry_cost = trade_val + buy_comm
            
            if total_entry_cost > portfolio["cash"]:
                qty = int(portfolio["cash"] / (actual_entry * (1 + COMMISSION)))
                trade_val = qty * actual_entry
                buy_comm = trade_val * COMMISSION
                total_entry_cost = trade_val + buy_comm
                
            if qty <= 0: continue
            
            safe_equity = max(portfolio["equity"], 1)
            current_heat = sum((abs(p['entry'] - p['sl']) * p['qty']) for p in portfolio["positions"].values()) / safe_equity
            new_heat = (risk * qty) / safe_equity
            sector = WATCHLIST[sym]
            sector_invested = sum((p['buy_value']) for s, p in portfolio["positions"].items() if WATCHLIST.get(s) == sector)
            new_sector_exposure = (sector_invested + trade_val) / safe_equity
            
            # Correlation Check (Look-ahead bias fixed)
            corr_safe = True
            hist_new = data_dict[sym].loc[:date, 'Close'].pct_change().dropna().tail(30)
            for open_sym in portfolio["positions"]:
                hist_open = data_dict[open_sym].loc[:date, 'Close'].pct_change().dropna().tail(30)
                corr_df = pd.concat([hist_new, hist_open], axis=1, join='inner').dropna()
                if len(corr_df) > 10: 
                    corr = corr_df.iloc[:,0].corr(corr_df.iloc[:,1])
                    if corr > 0.80:
                        corr_safe = False
                        portfolio["ledger"].append({"date": date, "action": "REJECTED_CORRELATION", "symbol": sym})
                        break
            
            if corr_safe and (current_heat + new_heat <= MAX_PORTFOLIO_HEAT) and (new_sector_exposure <= MAX_SECTOR_EXPOSURE):
                portfolio["cash"] -= total_entry_cost
                portfolio["positions"][sym] = {
                    'entry': actual_entry, 'sl': actual_sl, 'target': actual_target, 
                    'qty': qty, 'date': date, 'atr': sig['atr'], 
                    'buy_value': trade_val, 'buy_comm': buy_comm
                }
                portfolio["ledger"].append({"date": date, "action": "BUY", "symbol": sym, "price": actual_entry, "qty": qty})
                
        pending_signals = [] 
        
        # Mark-to-Market & Logging
        unrealized_pnl, invested_capital, current_heat = 0, 0, 0
        for sym, pos in portfolio["positions"].items():
            if date in data_dict[sym].index:
                close_p = data_dict[sym].loc[date, 'Close']
                est_sell_val = close_p * (1 - SLIPPAGE) * pos['qty']
                est_sell_comm = est_sell_val * COMMISSION
                unrealized_pnl += (est_sell_val - est_sell_comm - pos['buy_value'] - pos['buy_comm'])
                invested_capital += pos['buy_value']
                current_heat += (abs(pos['entry'] - pos['sl']) * pos['qty'])
                
        portfolio["equity"] = max(portfolio["cash"] + invested_capital + unrealized_pnl, 0) 
        exposure = min(invested_capital / max(portfolio["equity"], 1), 1.0)
        peak_equity = max(peak_equity, portfolio["equity"])
        current_dd = ((peak_equity - portfolio["equity"]) / peak_equity) * 100 if peak_equity > 0 else 0
        
        bench_equity = nifty_peak
if not nifty_hist.empty:
    # np.squeeze aur float() use karke Series ko wapas normal number banaya
    bench_equity = float(nifty_shares * np.squeeze(nifty_hist['Close'].iloc[-1]))
        
nifty_peak = max(nifty_peak, bench_equity)

            
        nifty_peak = max(nifty_peak, bench_equity)
        bench_dd = ((nifty_peak - bench_equity) / nifty_peak) * 100 if nifty_peak > 0 else 0
        
        portfolio["daily_log"].append({
            'date': date, 'equity': portfolio["equity"], 'cash': portfolio["cash"], 
            'exposure': exposure, 'positions_count': len(portfolio["positions"]), 
            'heat': current_heat / max(portfolio["equity"], 1), 'drawdown': current_dd,
            'benchmark_equity': bench_equity, 'benchmark_drawdown': bench_dd
        })

        # Scan Universe
        open_trades = [{"symbol": s} for s in portfolio["positions"]] 
        for sym in WATCHLIST:
            if sym in portfolio["positions"] or date not in data_dict[sym].index: continue
            hist = data_dict[sym].loc[:date]
            if len(hist) < 250: continue 
            atr = hist['ATR'].iloc[-1]
            if pd.isna(atr): continue 
            
            signal = evaluate_entry(sym, WATCHLIST[sym], hist, portfolio["equity"], open_trades, regime)
            if signal["status"] == "READY":
                pending_signals.append({'symbol': sym, 'score': signal['score'], 'atr': atr, 'signal_date': date})

    # EOD Force Close Remaining
    last_date = timeline[-1]
    for sym, pos in list(portfolio["positions"].items()):
        try: final_p = data_dict[sym]['Close'].iloc[-1] * (1 - SLIPPAGE)
        except: final_p = pos['entry']
            
        sell_val = final_p * pos['qty']
        sell_comm = sell_val * COMMISSION
        net_pnl = sell_val - sell_comm - pos['buy_value'] - pos['buy_comm']
        
        portfolio["cash"] += (sell_val - sell_comm)
        portfolio["trades"].append({"symbol": sym, "entry_date": pos['date'], "exit_date": last_date, "entry": pos['entry'], "exit": final_p, "qty": pos['qty'], "pnl": net_pnl})
        portfolio["ledger"].append({"date": last_date, "action": "EOD_FORCE_CLOSE", "symbol": sym, "price": final_p, "pnl": net_pnl})
        
    portfolio["positions"].clear()
    portfolio["equity"] = portfolio["cash"]

    # Exact CAPM Alpha & Beta
    df_log = pd.DataFrame(portfolio["daily_log"])
    alpha, beta = 0.0, 0.0
    if not df_log.empty and len(df_log) > 1:
        port_ret = df_log['equity'].pct_change().dropna()
        bench_ret = df_log['benchmark_equity'].pct_change().dropna()
        ret_df = pd.concat([port_ret, bench_ret], axis=1, join='inner').dropna()
        if len(ret_df) > 1:
            covar = np.cov(ret_df.iloc[:,0], ret_df.iloc[:,1])[0,1]
            var = np.var(ret_df.iloc[:,1])
            if var > 0 and np.isfinite(covar):
                beta = covar / var
                rf_daily = RF_RATE / 252
                excess_port = port_ret.mean() - rf_daily
                excess_bench = bench_ret.mean() - rf_daily
                alpha = (excess_port - beta * excess_bench) * 252 * 100

    days = (timeline[-1] - timeline[0]).days
    nifty_cagr = ((nifty_df['Close'].iloc[-1] / nifty_df['Close'].iloc[0]) ** (365.25/days) - 1) * 100 if not nifty_df.empty and days > 0 else 0
    portfolio["benchmark"] = {"Nifty_CAGR_%": nifty_cagr, "Alpha_%": alpha, "Beta": beta}
    
    return portfolio

# --- 4. BLOCK-BOOTSTRAP MONTE CARLO ---
def run_monte_carlo(trades_df, initial_capital=100000, simulations=1000, block_size=5):
    if trades_df.empty: return {}
    pnls = trades_df['pnl'].values
    blocks = [pnls[i:i+block_size] for i in range(0, len(pnls), block_size)]
    if not blocks: return {}
    
    sim_results = []
    ruin_count = 0
    ruin_threshold = initial_capital * RUIN_THRESHOLD 
    
    for _ in range(simulations):
        sim_blocks = np.random.choice(len(blocks), size=len(blocks), replace=True)
        sim_trades = np.concatenate([blocks[idx] for idx in sim_blocks])
        equity_curve = initial_capital + np.cumsum(sim_trades)
        
        peak = np.maximum.accumulate(equity_curve)
        dd = (peak - equity_curve) / peak
        
        if np.any(equity_curve < ruin_threshold): ruin_count += 1
        sim_results.append({'final_equity': equity_curve[-1], 'max_dd': np.max(dd) if len(dd) > 0 else 0})
        
    sim_df = pd.DataFrame(sim_results)
    return {
        "Total Simulations": simulations,
        "Risk of Ruin": f"{(ruin_count/simulations)*100:.2f}%",
        "Median Max Drawdown": f"{sim_df['max_dd'].median()*100:.2f}%",
        "99th Percentile Max Drawdown": f"{np.percentile(sim_df['max_dd'], 99)*100:.2f}%",
        "Pessimistic Final Equity (5th %ile)": f"₹{np.percentile(sim_df['final_equity'], 5):.2f}"
    }

# --- 5. PARAMETER STABILITY (WFO HEATMAP) ---
def run_parameter_stability(data_dict, nifty_df, timeline):
    sl_mults = [1.5, 2.0, 2.5]
    tp_mults = [3.0, 4.0, 5.0]
    results = []
    
    for sl, tp in itertools.product(sl_mults, tp_mults):
        print(f"Testing SL: {sl}x | TP: {tp}x...")
        res = run_portfolio_backtest(data_dict, nifty_df, timeline, sl_mult=sl, tp_mult=tp)
        trades_df = pd.DataFrame(res.get("trades", []))
        net_profit = trades_df['pnl'].sum() if not trades_df.empty else 0
        results.append({"SL Multiplier": sl, "TP Multiplier": tp, "Net Profit": net_profit, "Alpha": res.get("benchmark", {}).get("Alpha_%", 0)})
        
    return pd.DataFrame(results).pivot(index='SL Multiplier', columns='TP Multiplier', values='Net Profit')

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    print("Maddy AI V5.0: Initializing Data...")
    data_dict = {}
    for sym in WATCHLIST:
        df = yf.download(sym, period="2y", progress=False, auto_adjust=True)
        if not df.empty: data_dict[sym] = add_indicators(df)
        
    nifty_df = yf.download("^NSEI", period="2y", progress=False, auto_adjust=True)
    timeline = sorted(set().union(*[df.index for df in data_dict.values()]))
    
    print("\n--- 1. RUNNING CORE BACKTEST ---")
    base_result = run_portfolio_backtest(data_dict, nifty_df, timeline, sl_mult=2.0, tp_mult=4.0)
    trades_df = pd.DataFrame(base_result.get("trades", []))
    
    if not trades_df.empty:
        print(f"Total Trades Execute: {len(trades_df)}")
        print(f"Final Portfolio Equity: ₹{base_result['equity']:.2f}")
        print(f"Nifty CAGR: {base_result['benchmark']['Nifty_CAGR_%']:.2f}% | Alpha: {base_result['benchmark']['Alpha_%']:.2f}% | Beta: {base_result['benchmark']['Beta']:.2f}")
        
        print("\n--- 2. RUNNING MONTE CARLO SIMULATION (Block-Bootstrap) ---")
        mc_stats = run_monte_carlo(trades_df, INITIAL_CAPITAL, simulations=1000, block_size=5)
        for k, v in mc_stats.items(): print(f"{k}: {v}")
            
        print("\n--- 3. PARAMETER STABILITY HEATMAP ---")
        heatmap = run_parameter_stability(data_dict, nifty_df, timeline)
        print("\nNet Profit Heatmap (Rows: SL, Columns: TP):")
        print(heatmap)
    else:
        print("Not enough data or no trades executed.")
            
