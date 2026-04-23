import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI 15-Min Lab", layout="wide")
st.title("⚡ Maddy AI: 15-Min Two-Way Sniper")
st.write("Ab Maddy Dono Taraf Khelega! (Bullish 🟢 aur Bearish 🔴)")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "CIPLA.NS", "TATACHEM.NS", "TRENT.NS", "HINDALCO.NS", "HDFCBANK.NS", "AMBUJACEM.NS"])

if st.button("Start Two-Way Intraday Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka 15-min data load ho raha hai..."):
        df = yf.download(stock_symbol, period="1mo", interval="15m")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            # --- FILTERS ---
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))
            
            df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

            total_signals, target_hit, sl_hit, pending = 0, 0, 0, 0
            st.success("✅ Dono Taraf ke Filters Loaded! Scanning 15-min candles...")
            st.subheader("📊 Two-Way Trade Results:")
            
            start_index = max(50, len(df) - 400) 
            
            for i in range(start_index, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, trade_type, entry, sl, target = "", "", 0, 0, 0
                
                # --- TREND CONDITIONS ---
                is_uptrend = curr['Close'] > curr['EMA_50']
                is_downtrend = curr['Close'] < curr['EMA_50']
                is_high_volume = curr['Volume'] > (1.2 * curr['Vol_MA20'])
                
                # 🟢 BULLISH SETUP (Sirf Uptrend mein)
                if is_uptrend and curr['RSI'] < 60 and is_high_volume: 
                    # 1. Hammer
                    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                        pattern, trade_type = "🔨 Hammer", "BUY"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (1.5 * abs(entry - sl))
                        
                    # 2. Bullish Engulfing
                    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
                         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
                        pattern, trade_type = "🔥 Bull. Engulfing", "BUY"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 0.50
                        target = entry + (1.5 * abs(entry - sl))

                # 🔴 BEARISH SETUP (Sirf Downtrend mein)
                if is_downtrend and curr['RSI'] > 40 and is_high_volume:
                    # 3. Shooting Star (Ulta Hammer)
                    if upper_wick > (2 * body) and lower_wick < (0.5 * body) and curr['Close'] < prev['Close']:
                        pattern, trade_type = "☄️ Shooting Star", "SELL (Short)"
                        entry = curr['Low'] - 0.50
                        sl = curr['High'] + 0.50
                        target = entry - (1.5 * abs(entry - sl)) # Short mein target niche hota hai
                        
                    # 4. Bearish Engulfing
                    elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and \
                         (curr['Open'] >= prev['Close']) and (curr['Close'] <= prev['Open']):
                        pattern, trade_type = "🩸 Bear. Engulfing", "SELL (Short)"
                        entry = curr['Low'] - 0.50
                        sl = curr['High'] + 0.50
                        target = entry - (1.5 * abs(entry - sl))

                if pattern != "":
                    total_signals += 1
                    result = "⏳ Pending"
                    
                    # Time Machine Loop (Intraday)
                    check_limit = min(i + 25, len(df)) 
                    for j in range(i+1, check_limit):
                        future_candle = df.iloc[j]
                        
                        if trade_type == "BUY":
                            if future_candle['Low'] <= sl: result, sl_hit = "🔴 SL Hit", sl_hit + 1; break
                            elif future_candle['High'] >= target: result, target_hit = "🎯 Target Hit!", target_hit + 1; break
                                
                        elif trade_type == "SELL (Short)":
                            if future_candle['High'] >= sl: result, sl_hit = "🔴 SL Hit", sl_hit + 1; break
                            elif future_candle['Low'] <= target: result, target_hit = "🎯 Target Hit!", target_hit + 1; break
                    
                    if "Pending" in result: pending += 1
                    
                    message = f"{pattern_time} | {trade_type}: {pattern} | Entry: ₹{round(entry, 2)} | {result}"
                    if "Target" in result: st.success(message)
                    elif "SL" in result: st.error(message)
                    else: st.warning(message)

            # 🏆 Final Dashboard
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Trades", total_signals)
            col2.metric("🎯 Wins", target_hit)
            col3.metric("🔴 Losses", sl_hit)
            col4.metric("⏳ Pending", pending)
            
            completed_trades = target_hit + sl_hit
            if completed_trades > 0:
                win_rate = (target_hit / completed_trades) * 100
                st.info(f"🏆 Maddy AI Two-Way Win Rate: {round(win_rate, 2)}%")
                if win_rate >= 50: st.balloons()
            else:
                st.info("😎 Koi perfect setup nahi mila. Operator ke jaal se bache!")
                
