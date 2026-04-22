import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI Lab", layout="wide")
st.title("🧪 Maddy AI: 30-Day Profit/Loss Scanner")
st.write("Ab hum sirf signals nahi, unka Target aur Stop-Loss (SL) hit hua ya nahi, wo bhi check karenge!")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "SBIN.NS", "INFY.NS", "PAYTM.NS"])

if st.button("Start 30-Day P&L Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka data download aur calculate ho raha hai..."):
        df = yf.download(stock_symbol, period="1mo", interval="1h")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            total_signals = 0
            target_hit = 0
            sl_hit = 0
            pending = 0
            
            st.success("✅ Data Loaded! P&L Check Started...")
            st.subheader("📊 Trade Results:")
            
            # Har candle check karenge (last candle chhod kar)
            for i in range(5, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, entry, sl, target = "", 0, 0, 0
                
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

                if pattern != "":
                    total_signals += 1
                    result = "⏳ Pending (Target/SL dono hit nahi hue)"
                    
                    # 🚀 TIME MACHINE LOGIC: Aage ki candles mein jhak kar dekho
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
                    
                    # Screen par result print karo
                    if "Target" in result:
                        st.success(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")
                    elif "SL" in result:
                        st.error(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")
                    else:
                        st.warning(f"{pattern_time} | {pattern} | Entry: ₹{round(entry, 2)} | {result}")

            # 🏆 Final Dashboard
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Signals", total_signals)
            col2.metric("🎯 Target Hits (Wins)", target_hit)
            col3.metric("🔴 SL Hits (Losses)", sl_hit)
            col4.metric("⏳ Pending", pending)
            
            # Win Rate Calculation
            completed_trades = target_hit + sl_hit
            if completed_trades > 0:
                win_rate = (target_hit / completed_trades) * 100
                st.info(f"🏆 Maddy AI Win Rate: {round(win_rate, 2)}%")
                if win_rate >= 50:
                    st.balloons()
                    
