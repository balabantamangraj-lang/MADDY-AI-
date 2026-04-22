import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Lab", layout="wide")
st.title("🧪 Maddy AI: 30-Day Backtest Lab")
st.write("Yeh tool check karega ki pichle 30 dino mein Maddy ko kitne signals mile.")

# Dropdown menu stock select karne ke liye
stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "SBIN.NS", "INFY.NS", "PAYTM.NS"])

if st.button("Start 30-Day Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka data download ho raha hai..."):
        # 30 din ka data, 15 minute ke timeframe par
        df = yf.download(stock_symbol, period="1mo", interval="1h")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            signals_found = 0
            st.success(f"✅ Data Loaded! Total Candles: {len(df)}")
            
            st.subheader("📊 Signals History:")
            
            # Har candle ko check karne ka loop
            for i in range(5, len(df)):
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                
                # 1. Check Hammer
                if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                    st.info(f"🟢 {pattern_time} | 🔨 Hammer Found at ₹{round(curr['Close'], 2)}")
                    signals_found += 1
                
                # 2. Check Bullish Engulfing
                elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
                     (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
                    st.success(f"🔥 {pattern_time} | Bullish Engulfing at ₹{round(curr['Close'], 2)}")
                    signals_found += 1
            
            st.divider()
            st.metric(label="Total Signals Found in 30 Days", value=signals_found)
            if signals_found > 0:
                st.balloons()
              
