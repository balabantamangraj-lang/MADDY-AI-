import streamlit as st
import yfinance as yf
import pandas_ta as ta

# Page config
st.set_page_config(page_title="Maddy AI Pro", layout="wide")

st.title("🚀 Maddy AI: Live Buying Dashboard")
st.subheader("Maddy Special Edition 🔔")

# Stocks to track
watchlist = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS",
    "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "NTPC.NS", "TATASTEEL.NS",
    "ULTRACEMCO.NS", "POWERGRID.NS", "BAJAJ-AUTO.NS", "ASIANPAINT.NS", "ADANIPORTS.NS",
    "COALINDIA.NS", "BAJAJFINSV.NS", "GRASIM.NS", "M&M.NS", "WIPRO.NS",
    "JSWSTEEL.NS", "NESTLEIND.NS", "INDUSINDBK.NS", "HINDALCO.NS", "TECHM.NS",
    "CIPLA.NS", "DRREDDY.NS", "TRENT.NS", "BRITANNIA.NS", "APOLLOHOSP.NS",
    "EICHERMOT.NS", "DIVISLAB.NS", "HEROMOTOCO.NS", "BPCL.NS", "SHRIRAMFIN.NS",
    "BEL.NS", "HAL.NS", "ZOMATO.NS", "JIOFIN.NS", "TVSMOTOR.NS"
]


cols = st.columns(5)

for i, stock in enumerate(watchlist):
    with cols[i % 5]:
        try:
            df = yf.download(stock,period="1mo", interval="15m", progress=False)
            if not df.empty:
                price = round(df['Close'].iloc[-1], 2)
                rsi = round(ta.rsi(df['Close']).iloc[-1], 1)
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                
                st.metric(label=stock, value=f"₹{price}")
                
                if price > ema_200 and rsi > 55:
                    st.success("🟢 BUY NOW")
                else:
                    st.info("⚪ WAIT")
                st.caption(f"RSI: {rsi}")
        except:
            st.error(f"Error: {stock}")

# Auto-refresh har 1 minute mein
st.components.v1.html(
    """<script>setTimeout(function(){window.location.reload();}, 60000);</script>""",
    height=0,
)
