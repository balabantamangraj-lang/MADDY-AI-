import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

# 🛑 AAPKI TELEGRAM KEYS
TELEGRAM_TOKEN = "8512309562:AAGxWXADZfyzaH6fB4vuaIORRERnZ_QV664"
TELEGRAM_CHAT_ID = "-1003812569294"

def send_telegram_alert(bot_message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": bot_message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        st.error(f"Telegram Alert Failed: {e}")

# --- CUSTOM INDICATORS MATH ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window).mean()

# --- UI SETUP ---
st.set_page_config(page_title="Maddy AI Pro Engine", layout="wide")
st.title("🦅 Maddy AI: Pro Sniper Dashboard V2.2")
st.write("🔥 Institutional Accuracy | ATR Stoploss | Auto-Pilot Ready 🔥")

# 🤖 AUTO-PILOT MODE
auto_refresh = st.sidebar.checkbox("🤖 Enable Auto-Pilot (Scan every 5 mins)")
if auto_refresh:
    st.sidebar.success("Auto-Pilot Active! Maddy is watching... 🟢")

if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

watchlist = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", 
    "KOTAKBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HCLTECH.NS", 
    "TATAMOTORS.NS", "M&M.NS", "ITC.NS", "TITAN.NS", "ZOMATO.NS"
]

if st.button("🚨 Run High-Accuracy Scan") or auto_refresh:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ INTRADAY SNIPER (15-Min)")
    with col2:
        st.subheader("🚀 SWING ROCKET (1-Day)")
        
    intraday_found = False
    swing_found = False
    
    with st.spinner("⏳ Decoding Nifty Institutional Mood..."):
        try:
            nifty = yf.download("^NSEI", period="1mo", interval="1d", progress=False)
            # Fix 1: Nifty Multi-index columns flat kiye
            if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.droplevel(1)
            
            nifty['EMA_9'] = nifty['Close'].ewm(span=9, adjust=False).mean()
            nifty_mood = "POSITIVE" if nifty['Close'].iloc[-1] > nifty['EMA_9'].iloc[-1] else "NEGATIVE"
        except Exception as e:
            nifty_mood = "NEUTRAL"
            st.warning(f"Nifty Sync Issue: {e}")

    st.info(f"🧭 **Nifty Market Trend:** {nifty_mood}")
    progress_bar = st.progress(0)
    
    for i, stock in enumerate(watchlist):
        try:
            # ==========================================
            # 1. DAILY DATA (HTF Trend & Swing)
            # ==========================================
            df_daily = yf.download(stock, period="1y", interval="1d", progress=False)
            if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.droplevel(1)
            df_daily = df_daily.dropna()
            
            # Fix 2: Out-of-bounds safety check for Daily
            if len(df_daily) < 200:
                continue
            
            df_daily['EMA_50'] = df_daily['Close'].ewm(span=50, adjust=False).mean()
            df_daily['EMA_200'] = df_daily['Close'].ewm(span=200, adjust=False).mean()
            df_daily['52W_High'] = df_daily['High'].rolling(window=200).max().shift(1)
            df_daily['Vol_MA20'] = df_daily['Volume'].rolling(window=20).mean().shift(1)
            df_daily['RSI'] = calculate_rsi(df_daily['Close'])
            df_daily['ATR'] = calculate_atr(df_daily)
            
            today_d = df_daily.iloc[-1]
            
            s_trend = today_d['Close'] > today_d['EMA_50'] and today_d['EMA_50'] > today_d['EMA_200']
            s_breakout = today_d['Close'] >= (today_d['52W_High'] * 0.98) 
            s_volume = today_d['Volume'] > (2.0 * today_d['Vol_MA20'])
            s_rsi = 60 <= today_d['RSI'] <= 80
            
            if s_breakout and s_volume and s_trend and s_rsi and nifty_mood == "POSITIVE":
                with col2:
                    st.success(f"🔥 **[SWING]** {stock} | CMP: ₹{round(today_d['Close'],2)}")
                    st.write(f"✅ 2X Operator Volume | RSI: {round(today_d['RSI'],1)}")
                    atr_val = today_d['ATR']
                    entry = today_d['Close']
                    sl = entry - (2 * atr_val)  
                    tgt = entry + (4 * atr_val) 
                    st.info(f"🎯 Target: ₹{round(tgt,2)} | 🛑 SL: ₹{round(sl,2)}")
                    swing_found = True

                    if f"{stock}_swing" not in st.session_state.alerted_today:
                        msg = f"🚀 *MADDY VIP SWING ROCKET* 🚀\n✅ *Stock:* {stock}\n💰 *CMP:* ₹{round(entry, 2)}\n📈 *TARGET:* ₹{round(tgt, 2)}\n🛑 *STOP LOSS:* ₹{round(sl, 2)}\n🔥 _2X Volume Verified!_"
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[f"{stock}_swing"] = True

            # ==========================================
            # 2. INTRADAY DATA (15-Min Precision)
            # ==========================================
            df_15m = yf.download(stock, period="5d", interval="15m", progress=False)
            if isinstance(df_15m.columns, pd.MultiIndex): df_15m.columns = df_15m.columns.droplevel(1)
            df_15m = df_15m.dropna()
            
            # Fix 3: Out-of-bounds safety check for 15M
            if len(df_15m) < 50:
                continue
            
            df_15m['VWAP'] = (df_15m['Close'] * df_15m['Volume']).cumsum() / df_15m['Volume'].cumsum()
            df_15m['Support_Zone'] = df_15m['Low'].rolling(window=50).min().shift(1)
            df_15m['Vol_MA'] = df_15m['Volume'].rolling(window=10).mean().shift(1)
            df_15m['RSI'] = calculate_rsi(df_15m['Close'])
            
            today_15m = df_15m.iloc[-1]
            
            i_htf_trend = today_d['Close'] > today_d['EMA_200'] 
            i_vwap = today_15m['Close'] > today_15m['VWAP']     
            is_green_candle = today_15m['Close'] > today_15m['Open']
            at_support = today_15m['Low'] <= (today_15m['Support_Zone'] * 1.002)
            i_rsi = 45 <= today_15m['RSI'] <= 65 
            i_vol = today_15m['Volume'] > (1.5 * today_15m['Vol_MA'])
            
            if at_support and is_green_candle and i_vwap and i_htf_trend and i_rsi and i_vol and nifty_mood == "POSITIVE":
                with col1:
                    st.success(f"🟢 **[INTRADAY]** {stock} | CMP: ₹{round(today_15m['Close'],2)}")
                    st.write(f"✅ Green Support Bounce | Price > VWAP")
                    st.write(f"✅ 1.5x Vol Spike | RSI: {round(today_15m['RSI'],1)}")
                    st.info(f"🎯 Enter Above: ₹{round(today_15m['High'],2)} | 🛑 SL: ₹{round(today_15m['Low'],2)}")
                    intraday_found = True

                    if f"{stock}_intra" not in st.session_state.alerted_today:
                        msg = f"🟢 *MADDY VIP INTRADAY SNIPER* 🟢\n✅ *Stock:* {stock}\n💰 *CMP:* ₹{round(today_15m['Close'], 2)}\n🎯 *ENTRY ABOVE:* ₹{round(today_15m['High'], 2)}\n🛑 *STOP LOSS:* ₹{round(today_15m['Low'], 2)}\n⚖️ _VWAP Bounce Confirmed!_"
                        send_telegram_alert(msg)
                        st.session_state.alerted_today[f"{stock}_intra"] = True
                    
        except Exception as e:
            st.warning(f"⚠️ {stock} skipped due to error: {e}")
            
        progress_bar.progress((i + 1) / len(watchlist))

    st.divider()
    if not intraday_found:
        with col1: st.info("🔍 Intraday: No perfect setups right now.")
    if not swing_found:
        with col2: st.info("🔍 Swing: No strong volume breakouts today.")

if auto_refresh:
    time.sleep(300)
    st.rerun()
    
