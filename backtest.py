import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI: The Masterpiece", layout="wide")
st.title("🛡️ Maddy AI: The 'Concrete Floor' Masterpiece")
st.write("Ab Maddy 1 din ka kachra nahi, 4 din ka solid Support/Resistance dekhega! (Smart Money Concept)")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "CIPLA.NS", "TATACHEM.NS", "TRENT.NS", "HINDALCO.NS", "HDFCBANK.NS", "AMBUJACEM.NS"])

if st.button("Start Masterpiece Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka data load ho raha hai... (Jadoo shuru)"):
        df = yf.download(stock_symbol, period="1mo", interval="15m")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            # --- PRO LEVEL UPGRADE: 100 Candles (Approx 4 Days) Concrete Floor ---
            df['Support_100'] = df['Low'].rolling(window=100).min().shift(1)
            df['Resistance_100'] = df['High'].rolling(window=100).max().shift(1)
            df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

            total_signals, target_hit, sl_hit, pending = 0, 0, 0, 0
            st.success("✅ Concrete Zones Locked! Scanning Operator Traps...")
            st.subheader("📊 The Final Verdict:")
            
            start_index = max(105, len(df) - 400) 
            
            for i in range(start_index, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, trade_type, entry, sl, target = "", "", 0, 0, 0
                
                # Zone Logic: Price ko solid support/resistance ki range (0.3%) mein hona chahiye
                is_near_support = curr['Low'] <= (curr['Support_100'] * 1.003) and curr['Low'] >= (curr['Support_100'] * 0.997)
                is_near_resistance = curr['High'] >= (curr['Resistance_100'] * 0.997) and curr['High'] <= (curr['Resistance_100'] * 1.003)
                
                # Badi volume honi chahiye (Operator entry)
                is_high_volume = curr['Volume'] > (1.2 * curr['Vol_MA20']) 
                
                if is_near_support and is_high_volume: 
                    # 1. Hammer at Concrete Support
                    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                        pattern, trade_type = "🔨 Concrete Hammer", "BUY"
                        entry = curr['High'] + 0.50
                        # Operator Shield: SL is safe below the major 4-day support
                        sl = curr['Support_100'] * 0.995 
                        target = entry + (1.5 * abs(entry - sl))
                        
                if is_near_resistance and is_high_volume:
                    # 2. Shooting Star at Concrete Resistance
                    if upper_wick > (2 * body) and lower_wick < (0.5 * body) and curr['Close'] < prev['Close']:
                        pattern, trade_type = "☄️ Concrete Shooting Star", "SELL"
                        entry = curr['Low'] - 0.50
                        # Operator Shield: SL is safe above the major 4-day resistance
                        sl = curr['Resistance_100'] * 1.005
                        target = entry - (1.5 * abs(entry - sl))

                if pattern != "":
                    total_signals += 1
                    result = "⏳ Pending"
                    
                    check_limit = min(i + 25, len(df)) 
                    for j in range(i+1, check_limit):
                        future_candle = df.iloc[j]
                        if trade_type == "BUY":
                            if future_candle['Low'] <= sl: result, sl_hit = "🔴 SL Hit", sl_hit + 1; break
                            elif future_candle['High'] >= target: result, target_hit = "🎯 Target Hit!", target_hit + 1; break
                        elif trade_type == "SELL":
                            if future_candle['High'] >= sl: result, sl_hit = "🔴 SL Hit", sl_hit + 1; break
                            elif future_candle['Low'] <= target: result, target_hit = "🎯 Target Hit!", target_hit + 1; break
                    
                    if "Pending" in result: pending += 1
                    
                    message = f"{pattern_time} | {trade_type}: {pattern} | Entry: ₹{round(entry, 2)} | {result}"
                    if "Target" in result: st.success(message)
                    elif "SL" in result: st.error(message)
                    else: st.warning(message)

            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Trades", total_signals)
            col2.metric("🎯 Wins", target_hit)
            col3.metric("🔴 Losses", sl_hit)
            col4.metric("⏳ Pending", pending)
            
            completed_trades = target_hit + sl_hit
            if completed_trades > 0:
                win_rate = (target_hit / completed_trades) * 100
                st.info(f"🏆 Maddy Pro Win Rate: {round(win_rate, 2)}%")
                if win_rate >= 50: st.balloons()
            else:
                st.info("😎 Operator ko trap karne ka mauka nahi mila. Capital 100% Safe!")
                
