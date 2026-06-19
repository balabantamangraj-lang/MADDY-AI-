import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import sqlite3
import uuid
import traceback
from datetime import datetime

# ==========================================
# 🛑 1. SECURE CONFIG & OPTIMIZED SQLITE DB
# ==========================================
try:
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception:
    TELEGRAM_TOKEN = None
    TELEGRAM_CHAT_ID = None

DB_PATH = "maddy_production.db"

def init_db():
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS trades (
                        Trade_ID TEXT PRIMARY KEY,
                        Entry_Date TEXT,
                        Stock TEXT,
                        Sector TEXT,
                        Score INTEGER,
                        Pattern TEXT,
                        Regime TEXT,
                        Entry REAL,
                        SL REAL,
                        Target REAL,
                        Quantity INTEGER,
                        Status TEXT,
                        Exit_Price REAL,
                        Net_PnL REAL)''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(Status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stock ON trades(Stock);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster ON trades(Score, Pattern, Regime);")
init_db()

def send_telegram_alert(bot_message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": bot_message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        st.sidebar.error(f"TG Network Timeout/Error: {e}")

# ==========================================
# 💾 2. PORTFOLIO & BAYESIAN PROBABILITY
# ==========================================
def load_db():
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        return pd.read_sql_query("SELECT * FROM trades", conn)

def log_trade(trade_data):
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        try:
            conn.execute('''INSERT INTO trades 
                            (Trade_ID, Entry_Date, Stock, Sector, Score, Pattern, Regime, Entry, SL, Target, Quantity, Status, Exit_Price, Net_PnL) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)''', 
                         (trade_data['Trade_ID'], trade_data['Entry_Date'], trade_data['Stock'], trade_data['Sector'],
                          trade_data['Score'], trade_data['Pattern'], trade_data['Regime'], trade_data['Entry'], 
                          trade_data['SL'], trade_data['Target'], trade_data['Quantity'], trade_data['Status']))
            return True
        except sqlite3.IntegrityError:
            return False

def get_bayesian_probability(score, pattern, regime, db_df):
    if db_df.empty: return None 
    closed_trades = db_df[db_df['Status'].isin(['TP Hit 🟢', 'SL Hit 🔴', 'Gap SL 🩸'])]
    if len(closed_trades) < 10: return None 
    
    global_wins = len(closed_trades[closed_trades['Status'] == 'TP Hit 🟢'])
    global_mu = global_wins / len(closed_trades)
    
    bin_min = (score // 10) * 10
    subset = closed_trades[(closed_trades['Score'] >= bin_min) & (closed_trades['Score'] < bin_min + 10) & 
                           (closed_trades['Pattern'] == pattern) & (closed_trades['Regime'] == regime)]
                           
    N = len(subset)
    W = len(subset[subset['Status'] == 'TP Hit 🟢'])
    C = 30 
    
    return (W + C * global_mu) / (N + C)

# ==========================================
# ⚡ 3. RATE-LIMITED API & INDICATORS
# ==========================================
yf_session = requests.Session()

def clean_columns(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    return df

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, session=yf_session, progress=False)
    return clean_columns(df).dropna()

def calculate_wilders_rsi(data, window=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def calculate_macd(data):
    ema12 = data.ewm(span=12, adjust=False).mean()
    ema26 = data.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    return macd, macd.ewm(span=9, adjust=False).mean()

def calculate_wilders_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1/window, adjust=False).mean()

def detect_real_patterns(df, ema_20):
    cmp = df['Close'].iloc[-1]
    recent_highs = df['High'].iloc[-10:]
    recent_lows = df['Low'].iloc[-10:]
    recent_high_max = df['High'].iloc[-20:-1].max()
    
    vol_5d = df['Volume'].iloc[-5:].mean()
    vol_20d = df['Volume'].iloc[-20:].mean()
    vcp = vol_5d < vol_20d
    
    flat_base = (recent_highs.max() - recent_lows.min()) / recent_lows.min() < 0.04
    if flat_base and cmp > recent_high_max: return "Flat Base Breakout", 20
    touched_ema = df['Low'].iloc[-1] <= ema_20 * 1.01 and df['Low'].iloc[-1] >= ema_20 * 0.99
    if touched_ema and cmp > df['Open'].iloc[-1] and not vcp: return "EMA 20 Pullback Bounce", 15
    if cmp > recent_high_max and vcp: return "Resistance Breakout + VCP", 15
    return "Standard Structure", 0

# ==========================================
# 🖥️ 4. UI & EQUITY COMPOUNDING MANAGER
# ==========================================
st.set_page_config(page_title="Maddy AI Pro V16", layout="wide")
st.title("🦅 Maddy AI: V16.0 (Final Streamlit Build)")
st.markdown("🔥 **NaN Safe PnL | Zero-Division Safe RS | Full UUID Logging**")

st.sidebar.header("🏦 Capital Limits")
base_trading_capital = st.sidebar.number_input("Base Capital (₹)", value=100000, step=10000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 5.0, 1.0, step=0.1)

SECTOR_MAP = {
    "HDFCBANK.NS": "Banking", "ICICIBANK.NS": "Banking", "AXISBANK.NS": "Banking",
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy",
    "TCS.NS": "IT", "INFY.NS": "IT", "HCLTECH.NS": "IT",
    "TATAMOTORS.NS": "Auto", "M&M.NS": "Auto",
    "ZOMATO.NS": "Consumer Tech", "ITC.NS": "FMCG"
}
watchlist = list(SECTOR_MAP.keys())

# ==========================================
# 🚀 5. ALGO EXECUTION & BACKTEST
# ==========================================
if st.button("🚨 Run Apex Execution Tick"):
    st.divider()
    
    master_db = load_db()
    
    # 🔥 FIX 2: NaN Safe Realized PnL Calculation
    total_realized_pnl = master_db['Net_PnL'].fillna(0).sum() if not master_db.empty else 0
    current_equity = base_trading_capital + total_realized_pnl
    
    open_trades = master_db[master_db['Status'] == 'Open']
    locked_capital = (open_trades['Entry'] * open_trades['Quantity']).sum() if not open_trades.empty else 0
        
    available_capital = current_equity - locked_capital
    max_loss_amount = current_equity * (risk_per_trade_pct / 100) 
    
    with st.spinner("🌍 Processing Bayesian Analysis & PnL Reconciliations..."):
        for idx, row in master_db.iterrows():
            if row['Status'] == 'Open':
                eval_data = fetch_stock_data(row['Stock'], "6mo", "1d")
                entry_dt = pd.to_datetime(row['Entry_Date']).tz_localize(None)
                eval_data.index = eval_data.index.tz_localize(None)
                future_data = eval_data[eval_data.index > entry_dt]
                
                for date, candle in future_data.iterrows():
                    status = None
                    exit_price = None
                    
                    if candle['Open'] <= row['SL']:
                        status, exit_price = 'Gap SL 🩸', candle['Open']
                    elif candle['Low'] <= row['SL']: 
                        status, exit_price = 'SL Hit 🔴', row['SL']
                    elif candle['Open'] >= row['Target']:
                        status, exit_price = 'TP Hit 🟢', candle['Open']
                    elif candle['High'] >= row['Target']: 
                        status, exit_price = 'TP Hit 🟢', row['Target']

                    if status:
                        gross_pnl = (exit_price - row['Entry']) * row['Quantity']
                        turnover = (exit_price + row['Entry']) * row['Quantity']
                        charges = turnover * 0.001 
                        net_pnl = gross_pnl - charges
                        
                        with sqlite3.connect(DB_PATH, timeout=30) as conn:
                            conn.execute("UPDATE trades SET Status=?, Exit_Price=?, Net_PnL=? WHERE Trade_ID=?", 
                                         (status, exit_price, net_pnl, row['Trade_ID']))
                        break

    master_db = load_db()
    closed_trades = master_db[master_db['Status'].isin(['TP Hit 🟢', 'SL Hit 🔴', 'Gap SL 🩸'])]
    wins = len(closed_trades[closed_trades['Status'] == 'TP Hit 🟢'])
    total_closed = len(closed_trades)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    updated_net_pnl = closed_trades['Net_PnL'].fillna(0).sum() if not closed_trades.empty else 0
    updated_equity = base_trading_capital + updated_net_pnl
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Current Equity", f"₹{int(updated_equity)}", delta=f"{round((updated_equity/base_trading_capital - 1)*100, 2)}%")
    col_m2.metric("True Win Rate 🎯", f"{round(win_rate, 1)}%")
    col_m3.metric("Available Capital", f"₹{int(available_capital)}")
    col_m4.metric("Net Realized PnL 💸", f"₹{int(updated_net_pnl)}", delta_color="normal" if updated_net_pnl >= 0 else "inverse")
    
    st.divider()
    col_sig, col_log = st.columns([2, 1])
    with col_sig: st.subheader("⚡ Live Alpha Scans")
    with col_log: st.subheader("📂 Compounding Portfolio DB")
        
    progress_bar = st.progress(0)
        nifty_df = fetch_stock_data("^NSEI", "3mo", "1d")
    bn_df = fetch_stock_data("^NSEBANK", "3mo", "1d")
    vix_df = fetch_stock_data("^INDIAVIX", "3mo", "1d")
    
    # --- 🛠️ DEBUG MODE UI ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ API Debug Info")
    st.sidebar.write(f"Nifty Rows: `{len(nifty_df)}`")
    st.sidebar.write(f"BankNifty Rows: `{len(bn_df)}`")
    st.sidebar.write(f"VIX Rows: `{len(vix_df)}`")

    # --- 🛑 CRITICAL DATA CHECK ---
    if nifty_df.empty or bn_df.empty:
        st.error("🚨 Critical Market Data Unavailable (Yahoo Finance API Blocked/Empty). Please try again later.")
        st.stop() # Stops execution immediately safely

    # --- ⚖️ SAFE REGIME CALCULATION (VIX FALLBACK) ---
    if vix_df.empty:
        st.sidebar.warning("⚠️ VIX data missing from API. Running without VIX filter.")
        is_bull_market = (nifty_df['Close'].iloc[-1] > nifty_df['Close'].ewm(span=50).mean().iloc[-1]) and \
                         (bn_df['Close'].iloc[-1] > bn_df['Close'].ewm(span=50).mean().iloc[-1])
    else:
        is_bull_market = (nifty_df['Close'].iloc[-1] > nifty_df['Close'].ewm(span=50).mean().iloc[-1]) and \
                         (bn_df['Close'].iloc[-1] > bn_df['Close'].ewm(span=50).mean().iloc[-1]) and \
                         (vix_df['Close'].iloc[-1] < 20)
                         
    nifty_return = (nifty_df['Close'].iloc[-1] / nifty_df['Close'].iloc[-20]) - 1 if len(nifty_df) >= 20 else 0
    
    market_regime = "Bullish" if is_bull_market else "Bearish"
    market_score = 10 if is_bull_market else -15 

    
    for idx, stock in enumerate(watchlist):
        try:
            if available_capital <= 0:
                st.sidebar.warning("Capital Fully Deployed. Halting Scans.")
                break
                
            if not master_db[(master_db['Stock'] == stock) & (master_db['Status'] == 'Open')].empty: continue
            
            stock_sector = SECTOR_MAP.get(stock, "Unknown")
            if len(master_db[(master_db['Sector'] == stock_sector) & (master_db['Status'] == 'Open')]) >= 2: continue

            df_1d = fetch_stock_data(stock, "1y", "1d")
            if len(df_1d) < 100: continue
            if (df_1d['Close'] * df_1d['Volume']).rolling(20).mean().iloc[-1] < 100_000_000: continue 

            df_1h = fetch_stock_data(stock, "1mo", "1h")
            df_15m = fetch_stock_data(stock, "5d", "15m")
            if len(df_15m) < 30: continue
                
            stock_return = (df_1d['Close'].iloc[-1] / df_1d['Close'].iloc[-20]) - 1 if len(df_1d) >= 20 else 0
            
            # 🔥 FIX 1: Safe Division by Zero Check for Nifty Return
            if is_bull_market:
                if nifty_return > 0:
                    if (stock_return / nifty_return) < 1.2: continue 
                else:
                    if stock_return <= 0: continue # If Nifty is flat/down slightly, stock must be up
            else:
                if stock_return <= 0: continue 
                    
            df_1d['EMA_20'] = df_1d['Close'].ewm(span=20).mean()
            df_1d['Vol_MA20'] = df_1d['Volume'].rolling(20).mean().shift(1)
            df_1d['ATR'] = calculate_wilders_atr(df_1d) 
            
            df_1h['EMA_20'] = df_1h['Close'].ewm(span=20).mean()
            df_15m['EMA_20'] = df_15m['Close'].ewm(span=20).mean()
            df_15m['RSI'] = calculate_wilders_rsi(df_15m['Close'])
            df_15m['MACD'], df_15m['MACD_Sig'] = calculate_macd(df_15m['Close'])
            
            s_1d, s_1h, s_15m = df_1d.iloc[-1], df_1h.iloc[-1], df_15m.iloc[-1]
            cmp = s_15m['Close']
            
            score = 0
            if (cmp > s_15m['EMA_20']) and (s_1h['Close'] > s_1h['EMA_20']) and (s_1d['Close'] > s_1d['EMA_20']): score += 20
            if s_1d['Volume'] > (1.5 * s_1d['Vol_MA20']): score += 20
            if 55 <= s_15m['RSI'] <= 80: score += 15
            if s_15m['MACD'] > s_15m['MACD_Sig']: score += 15
            
            pattern_label, pattern_pts = detect_real_patterns(df_1d, s_1d['EMA_20'])
            if pattern_pts > 0: score += pattern_pts
            elif pattern_pts < 0: continue
            
            score += market_score
            
            if score >= 60:
                atr_val = s_1d['ATR']
                if pd.isna(atr_val) or atr_val <= 0: continue
                
                # Dynamic ATR Multiplier safe check
                sl_multiplier = 1.5
                if nifty_return > 0 and stock_return > (nifty_return * 2):
                    sl_multiplier = 1.5
                else:
                    sl_multiplier = 2.5
                    
                sl = cmp - (sl_multiplier * atr_val) 
                
                if sl >= cmp: continue
                risk_per_share = cmp - sl
                
                quantity = int(max_loss_amount / risk_per_share)
                position_value = quantity * cmp
                
                if position_value > (available_capital * 0.98): 
                    quantity = int((available_capital * 0.98) / cmp)
                    
                if quantity <= 0: continue 
                
                structural_res = df_1d['High'].rolling(50).max().shift(1).iloc[-1]
                target_1 = structural_res if (structural_res > (cmp + (1.5 * risk_per_share))) else cmp + (2.5 * risk_per_share)
                
                bayesian_prob = get_bayesian_probability(score, pattern_label, market_regime, master_db)
                prob_str = f"{round(bayesian_prob*100)}%" if bayesian_prob is not None else "Learning..."
                
                # 🔥 FIX 3: True UUID string implementation
                trade_id = str(uuid.uuid4()) 
                
                trade_data = {
                    "Trade_ID": trade_id, "Entry_Date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "Stock": stock, "Sector": stock_sector, "Score": score, "Pattern": pattern_label,
                    "Regime": market_regime, "Entry": round(cmp, 1), "SL": round(sl, 1), "Target": round(target_1, 1), 
                    "Quantity": quantity, "Status": "Open"
                }
                
                if log_trade(trade_data):
                    available_capital -= (quantity * cmp) 
                    with col_sig:
                        st.success(f"⚡ **{stock}** ({stock_sector}) -> **BUY 🟢**")
                        st.markdown(f"**Qty:** {quantity} | **Value:** ₹{int(quantity * cmp)} | **Pattern:** {pattern_label}")
                        st.info(f"💰 Entry: ₹{round(cmp,2)} | 🛑 SL: ₹{round(sl,2)} | 🎯 T1: ₹{round(target_1,2)}")
                    
                    msg = f"🏦 *SYSTEM SIGNAL*\n\nStock: {stock}\nProb: {prob_str}\nPattern: {pattern_label}\n\n💰 Entry: ₹{round(cmp, 1)}\n🛑 SL: ₹{round(sl, 1)}\n🎯 Target: ₹{round(target_1, 1)}\n\n⚖️ Qty: {quantity} shares\n💸 Value: ₹{int(quantity * cmp)}"
                    send_telegram_alert(msg)

        except Exception:
            st.sidebar.error(f"⚠️ {stock} Debug Trace:\n{traceback.format_exc()}")
            
        progress_bar.progress((idx + 1) / len(watchlist))
        
    with col_log:
        final_db = load_db()
        if not final_db.empty:
            st.dataframe(final_db[final_db['Status'] == 'Open'][['Stock', 'Entry', 'Target', 'Quantity']], use_container_width=True, hide_index=True)
        else:
            st.info("System Initialized. Scanning...")

