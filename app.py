import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time

# 🛑 Aapki Telegram Keys
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "7775145334"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        response = requests.post(url, data=data)
        
        # Naya Hatiyar: Agar Telegram fail hua toh screen par error dikhayega
        if response.status_code != 200:
            st.error(f"📱 Telegram Error: {response.text}")
            
    except Exception as e:
        st.error(f"📱 Telegram Crash: {e}")

# Page config
st.set_page_config(page_title="Maddy AI Pro", layout="wide")

st.title("🚀 Maddy AI: Live Buying Dashboard")
st.subheader("Maddy Special Edition 🔔")

# Testing ke liye Top 15 stocks
watchlist = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS"
]

cols = st.columns(5)

for i, stock in enumerate(watchlist):
    with cols[i % 5]:
        try:
            time.sleep(1.5) # Pause
            
            ticker = yf.Ticker(stock)
            df = ticker.history(period="1mo", interval="15m")
            
            if df is None or df.empty:
                pass
            elif len(df) < 200:
                pass
            else:
                rsi_series = ta.rsi(df['Close'])
                ema_series = ta.ema(df['Close'], length=200)
                
                if rsi_series is None or ema_series is None:
                    continue

                price = round(df['Close'].iloc[-1], 2)
                rsi = round(rsi_series.iloc[-1], 1)
                ema_200 = ema_series.iloc[-1]
                
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
            pass
            
