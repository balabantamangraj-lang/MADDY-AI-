import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

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

# Page Setup (Simple and Clean)
st.set_page_config(page_title="Maddy AI: Pattern Expert", layout="wide")
st.title("🚀 Maddy AI: Pattern Expert Dashboard")

# 🧠 Memory Setup
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}
    st.session_state.current_date = date.today()

watchlist = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS"
]

cols = st.columns(5)

for i, stock in enumerate(watchlist):
    with cols[i % 5]:
        try:
            time.sleep(1) 
            ticker = yf.Ticker(stock)
            df = ticker.history(period="3mo", interval="15m") 
            
            if not df.empty and len(df) > 200:
                # 🕯️ PATTERN DETECTION (Simplified)
                # Hum manually check karenge taaki library ki galti na ho
                op = df['Open']
                hi = df['High']
                lo = df['Low']
                cl = df['Close']
                
                # Indicators
                rsi = ta.rsi(cl).iloc[-1]
                ema_200 = ta.ema(cl, length=200).iloc[-1]
                price = round(cl.iloc[-1], 2)
                
                # Logic for Bullish Patterns
                pattern_found = ""
                
                # 1. Bullish Engulfing
                if cl.iloc[-1] > op.iloc[-2] and op.iloc[-1] < cl.iloc[-2] and cl.iloc[-2] < op.iloc[-2]:
                    pattern_found = "🔥 Bullish Engulfing"
                
                # 2. Hammer
                body = abs(cl.iloc[-1] - op.iloc[-1])
                lower_shadow = min(op.iloc[-1], cl.iloc[-1]) - lo.iloc[-1]
                if lower_shadow > (2 * body) and body > 0:
                    pattern_found = "🔨 Hammer"

                # UI Display
                st.metric(label=stock, value=f"₹{price}")

                if price > ema_200 and rsi > 55 and pattern_found != "":
                    target = round(price * 1.012, 2)
                    sl = round(price * 0.994, 2)
                    st.success(f"✅ {pattern_found}")
                    st.caption(f"🎯 {target} | 🛑 {sl}")

                    if stock not in st.session_state.alerted_today:
                        msg = f"🌟 MADDY PATTERN ALERT 🌟\n\n✅ {stock}\n🕯️ {pattern_found}\n💰 ₹{price}\n🎯 Tgt: ₹{target}\n🛑 SL: ₹{sl}"
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[stock] = True
                
                elif pattern_found != "":
                    st.warning(f"👀 {pattern_found}")
                else:
                    st.info("⚪ Searching...")
            else:
                st.error("Data Missing")
                    
        except Exception as e:
            pass
            
