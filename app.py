import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import date

# 🛑 AAPKI TELEGRAM KEYS (Ekdum Saaf)
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
# --- MEGA PATTERN SCANNER (All Major Patterns) ---
def check_patterns(df):
    if len(df) < 5: return "", 0, 0, 0
    
    prev2, prev, curr = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    body = abs(curr['Close'] - curr['Open'])
    lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
    upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
    prev_body = abs(prev['Close'] - prev['Open'])

    pattern, entry, sl, target = "", 0, 0, 0

    # 1. ⚖️ DOJI (Trend Reversal/Confusion)
    if body <= (curr['High'] - curr['Low']) * 0.1:
        pattern = "⚖️ Doji Pattern"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 2. ☄️ SHOOTING STAR (Bearish - Sell Signal)
    elif upper_wick > (2 * body) and lower_wick < (0.5 * body) and (curr['Close'] < prev['Close']):
        pattern = "☄️ Shooting Star (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50
        
    # 3. 🩸 BEARISH ENGULFING (Sell Signal)
    elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and \
         (curr['Open'] >= prev['Close']) and (curr['Close'] <= prev['Open']):
        pattern = "🩸 Bearish Engulfing (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50

    # 4. 🌙 EVENING STAR (Bearish Reversal - Sell Signal)
    elif (prev2['Close'] > prev2['Open']) and \
         (curr['Close'] < curr['Open']) and (curr['Close'] < (prev2['Open'] + prev2['Close']) / 2):
        pattern = "🌙 Evening Star (SELL)"
        entry = curr['Low'] - 0.50
        sl = curr['High'] + 0.50

    # 5. 🌅 MORNING STAR (Bullish - Buy Signal)
    elif (prev2['Close'] < prev2['Open']) and \
         (curr['Close'] > curr['Open']) and (curr['Close'] > (prev2['Open'] + prev2['Close']) / 2):
        pattern = "🌅 Morning Star (BUY)"
        entry = curr['High'] + 0.50
        sl = min(prev['Low'], curr['Low']) - 0.50
        
    # 6. 🔥 BULLISH ENGULFING (Buy Signal)
    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
        pattern = "🔥 Bullish Engulfing (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 7. 🔨 HAMMER (Buy Signal)
    elif lower_wick > (2 * body) and upper_wick < (0.5 * body) and (curr['Close'] > prev['Close']):
        pattern = "🔨 Hammer (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        
    # 8. ⚔️ PIERCING LINE (Strong Bullish - Buy Signal)
    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
         (curr['Open'] < prev['Low']) and (curr['Close'] > (prev['Open'] + prev['Close'])/2):
        pattern = "⚔️ Piercing Line (BUY)"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50

    # --- Target Calculation (1:2 Risk Reward) ---
    if pattern != "":
        if "SELL" in pattern:
            target = entry - (2 * abs(sl - entry)) # Sell ke liye target niche hoga
        else:
            target = entry + (2 * abs(entry - sl)) # Buy ke liye target upar hoga

    return pattern, entry, sl, target 
    
TELEGRAM_CHAT_ID = "-1003812569294"

# --- 1. NEW PATTERN & ENTRY/SL/TARGET LOGIC ---
def check_patterns(df):
    if len(df) < 2: return "", 0, 0, 0
    
    prev, curr = df.iloc[-2], df.iloc[-1]
    body = abs(curr['Close'] - curr['Open'])
    lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
    upper_wick = curr['High'] - max(curr['Open'], curr['Close'])

    pattern, entry, sl, target = "", 0, 0, 0

    # Bullish Engulfing
    if (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
       (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
        pattern = "🔥 Bullish Engulfing"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        target = entry + (2 * (entry - sl))

    # Hammer
    elif lower_wick > (2 * body) and upper_wick < (0.5 * body):
        pattern = "🔨 Hammer"
        entry = curr['High'] + 0.50
        sl = curr['Low'] - 0.50
        target = entry + (2 * (entry - sl))

    return pattern, entry, sl, target

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message}
        requests.post(url, data=data)
    except:
        pass

# --- Page UI Settings ---
st.set_page_config(page_title="Maddy AI Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00FFCC;'>🛡️ Maddy AI: VIP Scanner</h1>", unsafe_allow_html=True)

# 🧠 Memory Setup (Spam Control)
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

# 🔥 Watchlist (100 Stocks)
watchlist = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "HCLTECH.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "ASIANPAINT.NS", "LT.NS", "MARUTI.NS", "AXISBANK.NS", "SUNPHARMA.NS", "ADANIENT.NS", "TATAMOTORS.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
    "TITAN.NS", "COALINDIA.NS", "KOTAKBANK.NS", "ULTRACEMCO.NS", "JSWSTEEL.NS", "HINDALCO.NS", "TATASTEEL.NS", "ZOMATO.NS", "PFC.NS", "RECLTD.NS",
    "IRFC.NS", "RVNL.NS", "HAL.NS", "BEL.NS", "VBL.NS", "TRENT.NS", "TATACOMM.NS", "PETRONET.NS", "NHPC.NS", "MAZDOCK.NS",
    "IREDA.NS", "SUZLON.NS", "JIOFIN.NS", "PAYTM.NS", "YESBANK.NS", "IDFCFIRSTB.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS", "BANKBARODA.NS",
    "IOC.NS", "BPCL.NS", "GAIL.NS", "HINDPETRO.NS", "MRF.NS", "APOLLOTYRE.NS", "TVSMOTOR.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "ASHOKLEY.NS",
    "DLF.NS", "GODREJPROP.NS", "LODHA.NS", "OBEROIARL.NS", "TATACHEM.NS", "PIDILITIND.NS", "GRASIM.NS", "AMBUJACEM.NS", "ACC.NS", "SHREECEM.NS",
    "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "MANKIND.NS", "LTIM.NS", "TECHM.NS", "WIPRO.NS", "MPHASIS.NS", "PERSISTENT.NS",
    "DMART.NS", "TATAELXSI.NS", "DIXON.NS", "POLYCAB.NS", "KEI.NS", "HAVELLS.NS", "VOLTAS.NS", "BLUESTARCO.NS", "BHEL.NS", "SIEMENS.NS",
    "ABB.NS", "CUMMINSIND.NS", "CONCOR.NS", "INDIGO.NS", "NYKAA.NS", "DELHIVERY.NS", "IDEA.NS", "BOSCHLTD.NS", "COLPAL.NS", "JUBLFOOD.NS"
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

                # --- 2. SIGNAL ENGINE INTEGRATION ---
                # Check Patterns and get Entry/SL/Target prices
                pattern_name, entry_price, sl_price, target_price = check_patterns(df)

                # Check: Trend UP + Momentum + High Volume + PATTERN MATCHED
                if price > ema_200 and rsi > 50 and vol_current > (vol_avg * 1.3) and pattern_name != "":
                    
                    st.success(f"🎯 {pattern_name} DETECTED!")
                    st.write(f"🟢 Buy: ₹{round(entry_price, 2)} | 🛑 SL: ₹{round(sl_price, 2)}")
                    st.write(f"📈 Target: ₹{round(target_price, 2)}")

                    if stock not in st.session_state.alerted_today:
                        msg = f"🚀 *MADDY VIP ALERT* 🚀\n\n" \
                              f"✅ *Stock:* {stock}\n" \
                              f"🎯 *Pattern:* {pattern_name}\n\n" \
                              f"🟢 *BUY ABOVE:* ₹{round(entry_price, 2)}\n" \
                              f"🛑 *STOP LOSS:* ₹{round(sl_price, 2)}\n" \
                              f"📈 *TARGET:* ₹{round(target_price, 2)}\n\n" \
                              f"⚠️ *Rule:* Wait for price to cross 'Buy Above' level before entry!"
                        
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[stock] = True
                else:
                    st.info("⚪ Market Analysis...")
        except Exception as e:
            st.warning(f"⚠️ {stock} Scanning...")

st.divider()
st.subheader("💡 Accuracy Checklist")
st.info("1. Hammer (Hathoda) 🔨 | 2. Bullish Engulfing 🔥 | 3. Morning Star 🌅")
