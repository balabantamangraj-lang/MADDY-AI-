import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Lab", layout="wide")
st.title("🧪 Maddy AI: Pro Scanner with Trend Filter")
st.write("Ab Maddy sirf 'Upar Jate Hue' (Uptrend) market mein hi Buy karega. Bekaar signals ab band!")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "SBIN.NS", "INFY.NS", "PAYTM.NS"])

if st.button("Start P&L Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka data aur Trend filter load ho raha hai..."):
        # EMA sahi se calculate ho, isliye thoda zyada data download kar rahe hain
        df = yf.download(stock_symbol, period="3mo", interval="1h")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            # 🛡️ THE NEW UPGRADE: 50-EMA Trend Filter
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

            total_signals = 0
            target_hit = 0
            sl_hit = 0
            pending = 0
            
            st.success("✅ Data & Trend Filter Loaded! Scanning started...")
            st.subheader("📊 Smart Trade Results (Bekaar Trades Filtered):")
            
            # Pichle 1 mahine ka data check karenge (approx last 150 candles)
            start_index = max(5, len(df) - 150)
            
            for i in range(start_index, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, entry, sl, target = "", 0, 0, 0
                
                # 🛡️ THE CHECK: Kya stock sach mein Uptrend mein hai?
                is_uptrend = curr['Close'] > curr['EMA_50']
                
                if is_uptrend: # Sirf Uptrend mein Buy signals lenge
                    # 1. Check Hammer
                    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                        pattern = "🔨 Hammer"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (2 * abs(entry - sl)) # 1:2 Risk Reward
                        
                    # 2. Check Bullish Engulfing
                    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
                         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
                        pattern = "🔥 Bull. Engulfing"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (2 * abs(entry - sl))

                # Agar valid pattern mila toh check karo Target ya SL
                if pattern != "":
                    total_signals += 1
                    result = "⏳ Pending"
                    
                    # Time Machine Logic
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
                    
                    if "Target" in result:
                        st.success(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")
                    elif "SL" in result:
                        st.error(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")
                    else:
                        st.warning(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")

            # 🏆 Final Dashboard
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Smart Signals", total_signals)
            col2.metric("🎯 Target Hits (Wins)", target_hit)
            col3.metric("🔴 SL Hits (Losses)", sl_hit)
            col4.metric("⏳ Pending", pending)
            
            # Win Rate Calculation
            completed_trades = target_hit + sl_hit
            if completed_trades > 0:
                win_rate = (target_hit / completed_trades) * 100
                st.info(f"🏆 Maddy AI Win Rate (Filtered): {round(win_rate, 2)}%")
                if win_rate >= 50:
                    st.balloons()
            else:
                st.info("😎 Trend filter ne saare bekaar trades ko rok diya! Ek bhi galat trade nahi liya.")
                
