import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

# 🛑 AAPKI TELEGRAM KEYS (Vahi purani)
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "7775145334"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        requests.post(url, data=data)
    except:
        pass

# --- Page UI Settings ---
st.set_page_config(page_title="Maddy AI Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00FFCC;'>🛡️ Maddy AI: Pro Scanner</h1>", unsafe_allow_html=True)

# 🧠 Memory Setup (Spam Control)
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

# 🔥 Watchlist (Top Stocks for Fast Loading)
watchlist = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HCLTECH.NS", "ITC.NS", "SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "ADANIENT.NS"]

cols = st.columns(3) # 3 Column layout for better mobile view

for i, stock in enumerate(watchlist):
    with cols[i % 3]:
        try:
            time.sleep(0.5) # Fast scan
            ticker = yf.Ticker(stock)
            df = ticker.history(period="1mo", interval="15m")
            
            if not df.empty and len(df) > 50:
                # --- ACCURACY LOGIC ---
                rsi = ta.rsi(df['Close']).iloc[-1]
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                price = round(df['Close'].iloc[-1], 2)
                
                # Volume Logic (Current Volume vs Average)
                vol_current = df['Volume'].iloc[-1]
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

                st.metric(label=f"📊 {stock}", value=f"₹{price}")

                # --- SIGNAL ENGINE ---
                # Check: Trend is UP + Momentum is High + Big Players entering (Volume)
                if price > ema_200 and rsi > 55 and vol_current > (vol_avg * 1.3):
                    target = round(price + (price * 0.012), 2)
                    sl = round(price - (price * 0.006), 2)
                    
                    st.success("🎯 HIGH ACCURACY BUY")
                    st.write(f"✅ RSI: {round(rsi,1)} | 🔥 Vol: High")
                    st.write(f"📈 Target: {target} | 🛑 SL: {sl}")

                    # One Alert per Day
                    if stock not in st.session_state.alerted_today:
                        msg = f"🚀 MADDY VIP ALERT 🚀\n\n✅ {stock} BUY @ ₹{price}\n🎯 Target: ₹{target}\n🛑 SL: ₹{sl}\n\n⚠️ Check Hammer/Engulfing Pattern on Chart!"
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[stock] = True
                else:
                    st.info("⚪ Market Analysis...")
        except Exception as e:
            st.warning(f"⚠️ {stock} Scanning...")

# --- PRO TIPS FOR ACCURACY ---
st.divider()
st.subheader("💡 Accuracy Checklist (Manual Confirmation)")
st.write("Jab Maddy alert de, TradingView par ye zaroor dekhein:")
st.info("1. Hammer (Hathoda) 🔨 | 2. Bullish Engulfing (Badi Green Candle) 🔥 | 3. Morning Star 🌅")
