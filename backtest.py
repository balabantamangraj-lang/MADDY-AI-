import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Master Dashboard", layout="wide")
st.title("🦅 Maddy AI: The Ultimate Master Dashboard")
st.write("Ek Button. Do Radar. Intraday aur Swing dono ka Live Status! ⚡🚀")

# Aapki Combined Watchlist
watchlist = [
    "INDOTECH.NS", "STLTECH.NS", "LUXIND.NS", "SUVENLIFE.NS", 
    "GALLANTT.NS", "TRENT.NS", "TATACHEM.NS", "RELIANCE.NS", 
    "CIPLA.NS", "AMBUJACEM.NS", "HDFCBANK.NS"
]

st.info(f"📡 Master Radar tracking {len(watchlist)} stocks for both Intraday & Swing opportunities...")

if st.button("🚨 Run Master Scan (Intraday + Swing)"):
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ INTRADAY RADAR (15-Min)")
    with col2:
        st.subheader("🚀 SWING RADAR (1-Day)")
        
    intraday_found = False
    swing_found = False

    # Ek hi progress bar mein dono scan honge
    progress_bar = st.progress(0)
    
    for i, stock in enumerate(watchlist):
        # ---------------------------------------------------------
        # 1. INTRADAY SCANNER ENGINE (15-Min Concrete Floor)
        # ---------------------------------------------------------
        try:
            df_intra = yf.download(stock, period="1mo", interval="15m", progress=False)
            if not df_intra.empty and len(df_intra) > 105:
                if isinstance(df_intra.columns, pd.MultiIndex):
                    df_intra.columns = df_intra.columns.droplevel(1)
                df_intra = df_intra.dropna()
                
                df_intra['Support_100'] = df_intra['Low'].rolling(window=100).min().shift(1)
                df_intra['Resistance_100'] = df_intra['High'].rolling(window=100).max().shift(1)
                df_intra['Vol_MA20'] = df_intra['Volume'].rolling(window=20).mean().shift(1)
                
                today_i = df_intra.iloc[-1]
                prev_i = df_intra.iloc[-2]
                
                body = abs(today_i['Close'] - today_i['Open'])
                lower_wick = min(today_i['Open'], today_i['Close']) - today_i['Low']
                upper_wick = today_i['High'] - max(today_i['Open'], today_i['Close'])
                
                is_near_support = today_i['Low'] <= (today_i['Support_100'] * 1.003) and today_i['Low'] >= (today_i['Support_100'] * 0.997)
                is_near_resistance = today_i['High'] >= (today_i['Resistance_100'] * 0.997) and today_i['High'] <= (today_i['Resistance_100'] * 1.003)
                is_high_volume_i = today_i['Volume'] > (1.2 * today_i['Vol_MA20']) 
                
                with col1:
                    if is_near_support and is_high_volume_i and lower_wick > (2 * body) and today_i['Close'] > prev_i['Close']:
                        st.success(f"🟢 **[INTRADAY BUY]** {stock} | 🔨 Hammer at Support @ ₹{round(today_i['Close'], 2)}")
                        intraday_found = True
                    elif is_near_resistance and is_high_volume_i and upper_wick > (2 * body) and today_i['Close'] < prev_i['Close']:
                        st.error(f"🔴 **[INTRADAY SELL]** {stock} | ☄️ Shooting Star at Resist @ ₹{round(today_i['Close'], 2)}")
                        intraday_found = True
        except Exception:
            pass

        # ---------------------------------------------------------
        # 2. SWING SCANNER ENGINE (1-Day Rocket Breakout)
        # ---------------------------------------------------------
        try:
            df_swing = yf.download(stock, period="1y", interval="1d", progress=False)
            if not df_swing.empty and len(df_swing) > 200:
                if isinstance(df_swing.columns, pd.MultiIndex):
                    df_swing.columns = df_swing.columns.droplevel(1)
                df_swing = df_swing.dropna()
                
                df_swing['52W_High'] = df_swing['High'].rolling(window=200).max().shift(1)
                df_swing['Vol_MA20'] = df_swing['Volume'].rolling(window=20).mean().shift(1)
                
                today_s = df_swing.iloc[-1]
                entry_price = today_s['Close']
                
                is_breakout = entry_price > today_s['52W_High']
                is_vol_blast = today_s['Volume'] > (1.5 * today_s['Vol_MA20']) 
                
                with col2:
                    if is_breakout and is_vol_blast:
                        target = entry_price * 1.20
                        sl = entry_price * 0.93
                        st.success(f"🚀 **[SWING BUY]** {stock} | ₹{round(entry_price, 2)}\n\n🎯 TGT: ₹{round(target, 2)} | 🔴 SL: ₹{round(sl, 2)}")
                        swing_found = True
        except Exception:
            pass
            
        progress_bar.progress((i + 1) / len(watchlist))
    
    st.divider()
    if not intraday_found:
        with col1: st.info("😎 Koi Intraday Trap nahi mila.")
    if not swing_found:
        with col2: st.info("😎 Aaj koi Swing Breakout nahi hai.")
            
