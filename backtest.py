import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Maddy AI Pro Lab", layout="wide")
st.title("🧪 Maddy AI: 5-Step Master Algo Lab")
st.write("Trend + RSI + Volume + Mega Pattern = The Sniper Trade 🎯")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "SBIN.NS", "INFY.NS", "PAYTM.NS"])

if st.button("Start Ultimate Backtest"):
    with st.spinner(f"⏳ {stock_symbol} ka data aur 5-Step Filters load ho rahe hain..."):
        # 6 Mahine ka data lenge kyunki strict filter se bekaar trades filter ho jayenge
        df = yf.download(stock_symbol, period="6mo", interval="1h")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            # --- 1. EMA 50 (Trend Filter) ---
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

            # --- 2. RSI 14 (Sasta/Mehenga Filter) ---
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))

            # --- 3. Volume Average (Bada Paisa Filter) ---
            df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

            total_signals, target_hit, sl_hit, pending = 0, 0, 0, 0
            
            st.success("✅ All Institutional Filters Loaded! Scanning started...")
            st.subheader("📊 The 'Sniper' Trade Results:")
            
            start_index = max(50, len(df) - 500) 
            
            for i in range(start_index, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, entry, sl, target = "", 0, 0, 0
                
                # --- THE 5-STEP CHECK (The Magic Formula) ---
                is_uptrend = curr['Close'] > curr['EMA_50']
                is_sasta = curr['RSI'] < 50
                is_high_volume = curr['Volume'] > (1.2 * curr['Vol_MA20']) # Volume 20% zyada honi chahiye
                
                if is_uptrend and is_sasta and is_high_volume: 
                    # 1. Check Hammer
                    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                        pattern = "🔨 Hammer"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (2 * abs(entry - sl))
                        
                    # 2. Check Bullish Engulfing
                    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
                         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
                        pattern = "🔥 Bull. Engulfing"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (2 * abs(entry - sl))

                if pattern != "":
                    total_signals += 1
                    result = "⏳ Pending"
                    
                    # Time Machine Loop
                    for j in range(i+1, len(df)):
                        future_candle = df.iloc[j]
                        if future_candle['Low'] <= sl:
                            result = "🔴 SL Hit"
                            sl_hit += 1
                            break
                        elif future_candle['High'] >= target:
                            result = "🎯 Target Hit!"
                            target_hit += 1
                            break
                    
                    if "Pending" in result:
                        pending += 1
                    
                    message = f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | RSI: {round(curr['RSI'], 1)} | {result}"
                    if "Target" in result: st.success(message)
                    elif "SL" in result: st.error(message)
                    else: st.warning(message)

            # 🏆 Final Dashboard
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Sniper Signals", total_signals)
            col2.metric("🎯 Wins", target_hit)
            col3.metric("🔴 Losses", sl_hit)
            col4.metric("⏳ Pending", pending)
            
            completed_trades = target_hit + sl_hit
            if completed_trades > 0:
                win_rate = (target_hit / completed_trades) * 100
                st.info(f"🏆 Maddy AI Ultimate Win Rate: {round(win_rate, 2)}%")
                if win_rate >= 60:
                    st.balloons()
            else:
                st.info("😎 Strict filters on! Bekaar market mein Maddy ne trade lene se mana kar diya. Capital Safe!")
                
