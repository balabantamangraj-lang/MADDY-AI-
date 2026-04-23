import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Live Radar", layout="wide")
st.title("🚀 Maddy AI: LIVE Rocket Screener")
st.write("⏱️ **Golden Time:** Scan everyday at **3:15 PM - 3:25 PM** (Market band hone se thik pehle)")

# Aapki Swing Trading ki Watchlist
stocks_to_scan = [
    "INDOTECH.NS", "STLTECH.NS", "LUXIND.NS", "SUVENLIFE.NS", 
    "GALLANTT.NS", "TRENT.NS", "TATACHEM.NS", "RELIANCE.NS", 
    "CIPLA.NS", "AMBUJACEM.NS", "HDFCBANK.NS"
]

st.info(f"📡 Radar on {len(stocks_to_scan)} High-Momentum Stocks...")

if st.button("🚨 Scan LIVE Market Now"):
    with st.spinner("⏳ Operator ke footprints scan ho rahe hain..."):
        found_rockets = False
        
        for stock in stocks_to_scan:
            try:
                # 1 saal ka daily data live fetch kar rahe hain
                df = yf.download(stock, period="1y", interval="1d", progress=False)
                
                if df.empty or len(df) < 50:
                    continue
                
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                df = df.dropna()
                
                # --- LIVE BREAKOUT LOGIC ---
                # Pichle 200 din (lagbhag 1 saal) ka High
                df['52W_High'] = df['High'].rolling(window=200).max().shift(1)
                # Pichle 20 din ka Average Volume
                df['Vol_MA20'] = df['Volume'].rolling(window=20).mean().shift(1)
                
                # Aaj ka LIVE data (Last row)
                today = df.iloc[-1] 
                
                # Check: Kya aaj price 1-saal ki chhat tod raha hai?
                is_breakout = today['Close'] > today['52W_High']
                # Check: Kya aaj volume average se 1.5 guna zyada hai?
                is_vol_blast = today['Volume'] > (1.5 * today['Vol_MA20']) 
                
                if is_breakout and is_vol_blast:
                    st.success(f"🔥 **ROCKET ALERT:** {stock} | Live Price: ₹{round(today['Close'], 2)} | Status: Operator Volume Breakout!")
                    found_rockets = True
            except Exception as e:
                pass # Error aane par code ruke nahi, agle stock par jaye
                
        st.divider()
        if not found_rockets:
            st.warning("😎 Aaj koi Naya Rocket nahi mila. Zabaradasti trade nahi lenge. Capital Safe! Kal 3:15 PM par phir try karenge.")
            
