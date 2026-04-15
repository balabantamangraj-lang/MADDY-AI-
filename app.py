import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests

# 🛑 Aapki Telegram Keys
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "7775145334"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        requests.post(url, data=data)
    except:
        pass

# Page config
st.set_page_config(page_title="Maddy AI Pro", layout="wide")

st.title("🚀 Maddy AI: Live Buying Dashboard")
st.subheader("Maddy Special Edition 🔔")

# Testing ke liye abhi Top 15 stocks (Taaki Yahoo block na kare)
watchlist = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS"
]

cols = st.columns(5)

for i, stock in enumerate(watchlist):
    with cols[i % 5]:
        try:
            df = yf.download(stock, period="1mo", interval="15m", progress=False)
            
            # Agar data nahi aaya
            if df is None or df.empty:
                st.warning(f"⚠️ {stock}: Data Nahi Aaya")
            
            # Agar 200 candles se kam data hai (EMA ke liye)
            elif len(df) < 200:
                st.warning(f"⚠️ {stock}: Data Kam Hai ({len(df)} candles)")
                
            else:
                price = round(df['Close'].iloc[-1], 2)
                rsi = round(ta.rsi(df['Close']).iloc[-1], 1)
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                
                vol_current = df['Volume'].iloc[-1]
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

                st.metric(label=stock, value=f"₹{price}")

                if price > ema_200 and rsi > 55 and vol_current > vol_avg:
                    target = round(price + (price * 0.01), 2)
                    sl = round(price - (price * 0.005), 2)
                    
                    st.success(f"🟢 **BUY KARO!**\n🎯 ₹{target}\n🛑 ₹{sl}")
                    
                    # Telegram Trigger
                    alert_msg = f"🚨 Maddy VIP Alert 🚨\n\n🟢 {stock} BUY KARO!\n🎯 Target: ₹{target}\n🛑 Stop-Loss: ₹{sl}\n⚡ RSI: {rsi}"
                    send_telegram_alert(alert_msg)
                    
                else:
                    st.info(f"⚪ WAIT")
                    
        except Exception as e:
            # Agar koi aur math error aayi toh screen par print hogi!
            st.error(f"❌ {stock} Error: {e}")
            
