import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

# 🛑 Telegram Keys
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "7775145334"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        requests.post(url, data=data)
    except:
        pass

# Page Settings
st.set_page_config(page_title="Maddy AI Pro", layout="wide")
st.title("🚀 Maddy AI: Live Dashboard")

# Memory for Spam Control
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

# Watchlist (Stock list thodi choti ki hai taaki fast load ho)
watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "INFY.NS", "ITC.NS", "ADANIENT.NS"]

cols = st.columns(4)

for i, stock in enumerate(watchlist):
    with cols[i % 4]:
        try:
            # ⏳ Sirf 0.5 sec ka gap
            time.sleep(0.5)
            ticker = yf.Ticker(stock)
            df = ticker.history(period="1mo", interval="15m")
            
            if not df.empty and len(df) > 50:
                # Indicators (Wahi purana solid wala)
                rsi = ta.rsi(df['Close']).iloc[-1]
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                price = round(df['Close'].iloc[-1], 2)
                
                vol_current = df['Volume'].iloc[-1]
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

                st.metric(label=stock, value=f"₹{price}")

                if price > ema_200 and rsi > 55 and vol_current > vol_avg:
                    target = round(price + (price * 0.01), 2)
                    sl = round(price - (price * 0.005), 2)
                    
                    st.success(f"🟢 **BUY KARO!**")
                    st.write(f"🎯 {target} | 🛑 {sl}")

                    # Telegram (Only once)
                    if stock not in st.session_state.alerted_today:
                        alert_msg = f"🚀 Maddy Alert: {stock}\n💰 Price: ₹{price}\n🎯 Target: ₹{target}\n🛑 SL: ₹{sl}"
                        send_telegram_alert(alert_msg)
                        st.session_state.alerted_today[stock] = True
                else:
                    st.info("⚪ WAITING")
        except:
            st.error("⚠️ Data Error")
            
