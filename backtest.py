import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Live Radar", layout="wide")
st.title("🚀 Maddy AI: LIVE Rocket Screener (Pro Mode)")
st.write("⏱️ **Golden Time:** Scan everyday at **3:15 PM - 3:25 PM**")
st.write("🎯 **Strategy:** Swing Breakout (Hold for 2-4 weeks)")

# Aapki Swing Trading ki Watchlist
stocks_to_scan = [
    "INDOTECH.NS", "STLTECH.NS", "LUXIND.NS", "SUVENLIFE.NS", 
    "GALLANTT.NS", "TRENT.NS", "TATACHEM.NS", "RELIANCE.NS", 
    "CIPLA.NS", "AMBUJACEM.NS", "HDFCBANK.NS"
]

st.info(f"📡 Radar on {len(stocks_to_scan)} High-Momentum Stocks...")

if st.button("🚨 Scan LIVE Market Now"):
    with st.spinner("⏳ Operator ke footprints, Targets aur SL calculate ho rahe hain..."):
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
                df['52W_High'] = df['High'].rolling(window=200).max().shift(1)
                df['Vol_MA20'] = df['Volume'].rolling(window=20).mean().shift(1)
                
                today = df.iloc[-1] 
                entry_price = today['Close']
                
                is_breakout = entry_price > today['52W_High']
                is_vol_blast = today['Volume'] > (1.5 * today['Vol_MA20']) 
                
                if is_breakout and is_vol_blast:
                    # --- AUTO TARGET & SL CALCULATOR ---
                    target_price = entry_price * 1.20  # +20% Target
                    sl_price = entry_price * 0.93      # -7% Stop Loss
                    
                    st.success(f"🔥 **ROCKET ALERT:** {stock}")
                    st.markdown(f"""
                    * **🟢 Live Entry Price:** ₹{round(entry_price, 2)}
                    * **🎯 Target (20%):** ₹{round(target_price, 2)}
                    * **🔴 Stop-Loss (-7%):** ₹{round(sl_price, 2)}
                    """)
                    st.caption("💡 *Pro Tip: Jaise hi stock 10% profit mein aaye, apna SL utha kar Entry price par le aana (Trailing SL).*")
                    
                    found_rockets = True
            except Exception as e:
                pass 
                
        st.divider()
        if not found_rockets:
            st.warning("😎 Aaj koi Naya Rocket nahi mila. Zabaradasti trade nahi lenge. Capital Safe! Kal 3:15 PM par phir try karenge.")
            
