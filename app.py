import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

# 🛑 Aapki Telegram Keys (Vahi rehne di hain)
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "7775145334"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        requests.post(url, data=data)
    except:
        pass

# Page Styling
st.set_page_config(page_title="Maddy AI: Pattern Expert", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>🚀 Maddy AI: Pattern Expert Dashboard</h1>", unsafe_allow_html=True)

# 🧠 Memory Setup
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}
    st.session_state.current_date = date.today()

# Check Watchlist
watchlist = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS"
]

cols = st.columns(5)

for i, stock in enumerate(watchlist):
    with cols[i % 5]:
        try:
            time.sleep(1.2) # Thoda sa pause rate limit se bachne ke liye
            ticker = yf.Ticker(stock)
            df = ticker.history(period="2mo", interval="15m") # 2 months data for better EMA
            
            if df is not None and len(df) > 200:
                # 🕯️ CANDLESTICK PATTERN CALCULATION
                patterns = df.ta.cdl_pattern(name=["hammer", "engulfing", "morningstar"])
                
                # Indicators
                rsi_series = ta.rsi(df['Close'])
                ema_series = ta.ema(df['Close'], length=200)
                
                price = round(df['Close'].iloc[-1], 2)
                rsi = rsi_series.iloc[-1]
                ema_200 = ema_series.iloc[-1]
                
                # Pattern detection logic
                current_pattern = ""
                # Check current and previous candle
                if patterns['CDL_ENGULFING'].iloc[-1] > 0: current_pattern = "🔥 Bullish Engulfing"
                elif patterns['CDL_HAMMER'].iloc[-1] > 0: current_pattern = "🔨 Hammer"
                elif patterns['CDL_MORNINGSTAR'].iloc[-1] > 0: current_pattern = "🌅 Morning Star"

                # Metrics Display
                st.metric(label=stock, value=f"₹{price}")

                # 🛠️ THE STRATEGY ENGINE
                if price > ema_200 and rsi > 55 and current_pattern != "":
                    target = round(price + (price * 0.012), 2) # 1.2% Target
                    sl = round(price - (price * 0.006), 2)    # 0.6% SL
                    
                    st.success(f"✅ BUY: {current_pattern}")
                    st.write(f"🎯 Tgt: {target} | 🛑 SL: {sl}")

                    # Telegram Trigger (Only once per day per stock)
                    if stock not in st.session_state.alerted_today:
                        msg = f"🌟 MADDY PATTERN ALERT 🌟\n\n✅ STOCK: {stock}\n🕯️ PATTERN: {current_pattern}\n💰 PRICE: ₹{price}\n🎯 TARGET: ₹{target}\n🛑 STOP-LOSS: ₹{sl}\n⚡ RSI: {round(rsi,1)}"
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[stock] = True
                
                elif current_pattern != "":
                    st.warning(f"👀 {current_pattern} (Waiting for Confirmation)")
                else:
                    st.info("⚪ Searching Patterns...")
                    
        except Exception as e:
            st.error(f"Error in {stock}")
            
