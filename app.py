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

st.set_page_config(page_title="Maddy AI: Pattern Expert", layout="wide")
st.title("🚀 Maddy AI: Pattern Expert Dashboard")

if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "INFY.NS", "ITC.NS", "ADANIENT.NS"]

cols = st.columns(4)

for i, stock in enumerate(watchlist):
    with cols[i % 4]:
        try:
            time.sleep(1)
            ticker = yf.Ticker(stock)
            df = ticker.history(period="1mo", interval="15m")
            
            if not df.empty:
                # Indicators
                rsi = ta.rsi(df['Close']).iloc[-1]
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                price = round(df['Close'].iloc[-1], 2)

                # Simplified Pattern Detection
                # 🔨 Hammer Check
                is_hammer = (df['High'] - df['Low'] > 3 * abs(df['Open'] - df['Close'])) and \
                            (df['Close'] > df['Open']) and \
                            (df['High'] - df['Close'] < 0.1 * (df['High'] - df['Low']))
                
                pattern_found = ""
                if is_hammer.iloc[-1]: pattern_found = "🔨 Hammer"

                st.metric(label=stock, value=f"₹{price}")

                if price > ema_200 and rsi > 55:
                    if pattern_found != "":
                        st.success(f"✅ BUY: {pattern_found}")
                        if stock not in st.session_state.alerted_today:
                            send_telegram_alert(f"🚀 Maddy Alert: {stock} @ ₹{price}\nPattern: {pattern_found}")
                            st.session_state.alerted_today[stock] = True
                    else:
                        st.info("⚪ Wait for Pattern")
                else:
                    st.info("⚪ Searching...")
        except:
            st.error("⚠️ Loading...")
            
