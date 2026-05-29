import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- CUSTOM INDICATORS MATH ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window).mean()

# --- UI SETUP ---
st.set_page_config(page_title="Maddy AI Pro Engine", layout="wide")
st.title("🦅 Maddy AI: Pro Sniper Dashboard V2.0")
st.write("🔥 Institutional Accuracy | ATR Stoploss | RSI Momentum Filter 🔥")

watchlist = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", 
    "KOTAKBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HCLTECH.NS", 
    "TATAMOTORS.NS", "M&M.NS", "ITC.NS", "TITAN.NS", "ZOMATO.NS"
    # Add more stocks as needed, keeping list manageable for speed
]

if st.button("🚨 Run High-Accuracy Scan"):
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ INTRADAY SNIPER (15-Min)")
    with col2:
        st.subheader("🚀 SWING ROCKET (1-Day)")
        
    intraday_found = False
    swing_found = False
    
    # Global Sector Sync (Nifty Mood)
    with st.spinner("⏳ Decoding Nifty Institutional Mood..."):
        try:
            nifty = yf.download("^NSEI", period="10d", interval="1d", progress=False)
            nifty['EMA_9'] = nifty['Close'].ewm(span=9, adjust=False).mean()
            nifty_mood = "POSITIVE" if nifty.iloc[-1]['Close'].values[0] > nifty.iloc[-1]['EMA_9'].values[0] else "NEGATIVE"
        except:
            nifty_mood = "NEUTRAL"

    st.info(f"🧭 **Nifty Market Trend:** {nifty_mood}")
    progress_bar = st.progress(0)
    
    for i, stock in enumerate(watchlist):
        try:
            # ==========================================
            # 1. DAILY DATA (HTF Trend & Swing)
            # ==========================================
            df_daily = yf.download(stock, period="1y", interval="1d", progress=False)
            if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.droplevel(1)
            df_daily = df_daily.dropna()
            
            # Indicators
            df_daily['EMA_50'] = df_daily['Close'].ewm(span=50, adjust=False).mean()
            df_daily['EMA_200'] = df_daily['Close'].ewm(span=200, adjust=False).mean()
            df_daily['52W_High'] = df_daily['High'].rolling(window=200).max().shift(1)
            df_daily['Vol_MA20'] = df_daily['Volume'].rolling(window=20).mean().shift(1)
            df_daily['RSI'] = calculate_rsi(df_daily['Close'])
            df_daily['ATR'] = calculate_atr(df_daily)
            
            today_d = df_daily.iloc[-1]
            prev_d = df_daily.iloc[-2]
            
            # --- HIGH-ACCURACY SWING LOGIC ---
            # 1. Trend Filter
            s_trend = today_d['Close'] > today_d['EMA_50'] and today_d['EMA_50'] > today_d['EMA_200']
            # 2. Breakout Filter (Closing near or above 52W High)
            s_breakout = today_d['Close'] >= (today_d['52W_High'] * 0.98) 
            # 3. Smart Money Volume (200% Volume Spike)
            s_volume = today_d['Volume'] > (2.0 * today_d['Vol_MA20'])
            # 4. Momentum (Not Overbought)
            s_rsi = 60 <= today_d['RSI'] <= 80
            
            if s_breakout and s_volume and s_trend and s_rsi and nifty_mood == "POSITIVE":
                with col2:
                    st.success(f"🔥 **[SWING]** {stock} | CMP: ₹{round(today_d['Close'],2)}")
                    st.write(f"✅ 2X Operator Volume | RSI: {round(today_d['RSI'],1)}")
                    # Dynamic ATR Target & Stoploss
                    atr_val = today_d['ATR']
                    entry = today_d['Close']
                    sl = entry - (2 * atr_val)  # 2x ATR Stoploss
                    tgt = entry + (4 * atr_val) # 1:2 Risk Reward
                    st.info(f"🎯 Target: ₹{round(tgt,2)} | 🛑 SL: ₹{round(sl,2)}")
                    swing_found = True

            # ==========================================
            # 2. INTRADAY DATA (15-Min Precision)
            # ==========================================
            df_15m = yf.download(stock, period="5d", interval="15m", progress=False)
            if isinstance(df_15m.columns, pd.MultiIndex): df_15m.columns = df_15m.columns.droplevel(1)
            df_15m = df_15m.dropna()
            
            df_15m['VWAP'] = (df_15m['Close'] * df_15m['Volume']).cumsum() / df_15m['Volume'].cumsum()
            df_15m['Support_Zone'] = df_15m['Low'].rolling(window=50).min().shift(1)
            df_15m['Vol_MA'] = df_15m['Volume'].rolling(window=10).mean().shift(1)
            df_15m['RSI'] = calculate_rsi(df_15m['Close'])
            
            today_15m = df_15m.iloc[-1]
            
            # --- HIGH-ACCURACY INTRADAY LOGIC ---
            i_htf_trend = today_d['Close'] > today_d['EMA_200'] # Daily UP trend
            i_vwap = today_15m['Close'] > today_15m['VWAP']     # Above VWAP
            
            # Bounce Confirmation (Green Candle at Support)
            is_green_candle = today_15m['Close'] > today_15m['Open']
            at_support = today_15m['Low'] <= (today_15m['Support_Zone'] * 1.002)
            
            # Intraday Momentum & Volume
            i_rsi = 45 <= today_15m['RSI'] <= 65 # Fresh move starting
            i_vol = today_15m['Volume'] > (1.5 * today_15m['Vol_MA'])
            
            if at_support and is_green_candle and i_vwap and i_htf_trend and i_rsi and i_vol and nifty_mood == "POSITIVE":
                with col1:
                    st.success(f"🟢 **[INTRADAY]** {stock} | CMP: ₹{round(today_15m['Close'],2)}")
                    st.write(f"✅ Green Support Bounce | Price > VWAP")
                    st.write(f"✅ 1.5x Vol Spike | RSI: {round(today_15m['RSI'],1)}")
                    st.info(f"🎯 Enter Above: ₹{round(today_15m['High'],2)} | 🛑 SL: ₹{round(today_15m['Low'],2)}")
                    intraday_found = True
                    
        except Exception as e:
            pass 
            
        progress_bar.progress((i + 1) / len(watchlist))

    st.divider()
    if not intraday_found:
        with col1: st.warning("🔍 Intraday: No 100% accurate setups right now. Waiting for perfect VWAP bounce.")
    if not swing_found:
        with col2: st.warning("🔍 Swing: No strong volume breakouts today.")

