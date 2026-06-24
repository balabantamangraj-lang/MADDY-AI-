import pandas as pd, numpy as np, yfinance as yf
from datetime import datetime
import itertools
import warnings
warnings.filterwarnings('ignore')

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
    
    # Safely extract initial nifty price
    if not nifty_df.empty:
        initial_nifty_price = float(np.squeeze(nifty_df['Close'].iloc[0]))
        nifty_shares = INITIAL_CAPITAL / initial_nifty_price if initial_nifty_price > 0 else 0
    else:
        nifty_shares = 0
        
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
            
            # Correlation Check
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
            bench_equity = float(nifty_shares * np.squeeze(nifty_hist['Close'].iloc[-1]))
            
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
        try: 
            final_p = data_dict[sym]['Close'].iloc[-1] * (1 - SLIPPAGE)
        except: 
            final_p = pos['entry']
            
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
    alpha, beta = 0.0
        
