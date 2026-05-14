import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

# 🛑 AAPKI TELEGRAM KEYS
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "-1003812569294"
# --- 1. MEGA PATTERN SCANNER (Candlestick + Advanced Chart Patterns) ---
def check_patterns(df):
    if len(df) < 25: return "", 0, 0, 0 # Advanced patterns ke liye zyada data chahiye
    
    prev2, prev, curr = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    # Basic Candlestick Math
    body = abs(curr['Close'] - curr['Open'])
    lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
    upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
    prev_body = abs(prev['Close'] - prev['Open'])

    pattern, entry, sl, target = "", 0, 0, 0

    # ==========================================
    # 🌟 ADVANCED CHART PATTERNS (Macro Vision)
    # ==========================================
    
    # 1. 📦 THE PRESSURE COOKER (Consolidation Box Breakout)
    last_20_days = df.iloc[-21:-1] 
    box_high = last_20_days['High'].max()
    box_low = last_20_days['Low'].min()
    box_range_percent = ((box_high - box_low) / box_low) * 100
    
    if box_range_percent < 6.0 and curr['Close'] > box_high:
        pattern = "📦 Pressure Cooker (Box Breakout) BUY"
        entry = curr['Close'] + 0.50
        sl = box_low 
        target = entry + (2 * (entry - sl))
        return pattern, entry, sl, target

    # 2. 📈 THE "W" PATTERN (Double Bottom Reversal)
    recent_support = df['Low'].iloc[-20:-5].min()
    if curr['Close'] > prev['Close'] and (curr['Low'] <= recent_support * 1.01) and (curr['Low'] >= recent_support * 0.99):
         pattern = "📈 'W' Pattern (Double Bottom) BUY"
         entry = curr['High'] + 0.50
         sl = recent_support * 0.99 
         target = entry + (2 * (entry - sl))
         return pattern, entry, sl, target

    # ==========================================
    # 🕯️ CANDLESTICK PATTERNS (Micro Vision)
    # ==========================================
    
    # 1. ⚖️ DOJI
    if body <= (curr['High'] - curr['Low']) * 0.1:
        pattern = "⚖️ Doji Pattern"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 2. ☄️ SHOOTING STAR (SELL)
    elif upper_wick > (2 * body) and lower_wick < (0.5 * body) and (curr['Close'] < prev['Close']):
        pattern = "☄️ Shooting Star (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50
        
    # 3. 🩸 BEARISH ENGULFING (SELL)
    elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and \
         (curr['Open'] >= prev['Close']) and (curr['Close'] <= prev['Open']):
        pattern = "🩸 Bearish Engulfing (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50

    # 4. 🌙 EVENING STAR (SELL)
    elif (prev2['Close'] > prev2['Open']) and \
         (curr['Close'] < curr['Open']) and (curr['Close'] < (prev2['Open'] + prev2['Close']) / 2):
        pattern = "🌙 Evening Star (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50

    # 5. 🌅 MORNING STAR (BUY)
    elif (prev2['Close'] < prev2['Open']) and \
         (curr['Close'] > curr['Open']) and (curr['Close'] > (prev2['Open'] + prev2['Close']) / 2):
        pattern = "🌅 Morning Star (BUY)"
        entry = curr['High'] + 0.50
        sl = min(prev['Low'], curr['Low']) - 0.50
        
    # 6. 🔥 BULLISH ENGULFING (BUY)
    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
        pattern = "🔥 Bullish Engulfing (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 7. 🔨 HAMMER (BUY)
    elif lower_wick > (2 * body) and upper_wick < (0.5 * body) and (curr['Close'] > prev['Close']):
        pattern = "🔨 Hammer (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 8. ⚔️ PIERCING LINE (BUY)
    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
         (curr['Open'] < prev['Low']) and (curr['Close'] > (prev['Open'] + prev['Close'])/2):
        pattern = "⚔️ Piercing Line (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50

    # --- Target Calculation ---
    if pattern != "":
        if "SELL" in pattern:
            target = entry - (2 * abs(sl - entry)) 
        else:
            target = entry + (2 * abs(entry - sl)) 

    return pattern, entry, sl, target 




# --- 2. TELEGRAM ALERT ENGINE ---
def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        pass

# --- Page UI Settings ---
st.set_page_config(page_title="Maddy AI Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00FFCC;'>🛡️ Maddy AI: VIP Scanner</h1>", unsafe_allow_html=True)

# Memory Setup (Spam Control)
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

# 🔥 Watchlist (Top 10 Stocks for quick test, you can expand to 100 later)
watchlist = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "HCLTECH.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS"
]

cols = st.columns(3)

for i, stock in enumerate(watchlist):
    with cols[i % 3]:
        try:
            time.sleep(0.5) 
            ticker = yf.Ticker(stock)
            df = ticker.history(period="1mo", interval="15m")
            
            if not df.empty and len(df) > 50:
                rsi = ta.rsi(df['Close']).iloc[-1]
                ema_200 = ta.ema(df['Close'], length=200).iloc[-1]
                price = round(df['Close'].iloc[-1], 2)
                
                vol_current = df['Volume'].iloc[-1]
                vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

                st.metric(label=f"📊 {stock}", value=f"₹{price}")

                # Pattern Scan
                pattern_name, entry_price, sl_price, target_price = check_patterns(df)

                # ✅ RULE ENGINE: Trend + Momentum + Volume + Pattern
                if pattern_name != "":
                    is_valid_trade = False
                    trade_type = ""
                    
                    # Buy Logic (Above EMA, RSI > 50)
                    if "BUY" in pattern_name and price > ema_200 and rsi > 50 and vol_current > (vol_avg * 1.3):
                        is_valid_trade = True
                        trade_type = "🟢 BUY"
                    
                    # Sell Logic (Below EMA, RSI < 50) - Optional Pro feature
                    elif "SELL" in pattern_name and price < ema_200 and rsi < 50 and vol_current > (vol_avg * 1.3):
                        is_valid_trade = True
                        trade_type = "🔴 SELL"
                    
                    if is_valid_trade:
                        st.success(f"🎯 {pattern_name} DETECTED!")
                        st.write(f"{trade_type}: ₹{round(entry_price, 2)} | 🛑 SL: ₹{round(sl_price, 2)}")
                        st.write(f"📈 Target: ₹{round(target_price, 2)}")

                        if stock not in st.session_state.alerted_today:
                            msg = f"🚀 *MADDY VIP ALERT* 🚀\n\n" \
                                  f"✅ *Stock:* {stock}\n" \
                                  f"🎯 *Pattern:* {pattern_name}\n\n" \
                                  f"{trade_type} *ABOVE/BELOW:* ₹{round(entry_price, 2)}\n" \
                                  f"🛑 *STOP LOSS:* ₹{round(sl_price, 2)}\n" \
                                  f"📈 *TARGET:* ₹{round(target_price, 2)}\n\n" \
                                  f"⚠️ *Rule:* Wait for price confirmation!"
                            
                            send_telegram_alert(msg)
                            st.session_state.alerted_today[stock] = True
                else:
                    st.info("⚪ Market Analysis...")
        except Exception as e:
            st.warning(f"⚠️ {stock} Scanning...")

st.divider()
st.subheader("💡 Accuracy Checklist")
st.info("1. Hammer (Hathoda) 🔨 | 2. Bullish Engulfing 🔥 | 3. Morning Star 🌅")
