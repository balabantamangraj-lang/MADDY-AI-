import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Maddy AI: Price Action Lab", layout="wide")
st.title("⚡ Maddy AI: Pure Price Action (Support/Resistance)")
st.write("No RSI, No EMA! Sirf Zameen (Support) aur Chhat (Resistance) par trade! 🏛️")

stock_symbol = st.selectbox("Stock Select Kijiye:", ["RELIANCE.NS", "CIPLA.NS", "TATACHEM.NS", "TRENT.NS", "HINDALCO.NS", "HDFCBANK.NS", "AMBUJACEM.NS"])

if st.button("Start Price Action Scan"):
    with st.spinner(f"⏳ {stock_symbol} ka 15-min data load ho raha hai..."):
        df = yf.download(stock_symbol, period="1mo", interval="15m")
        
        if df.empty:
            st.error("Data download nahi hua! Yahoo Finance issue.")
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = df.dropna()

            # --- PURE PRICE ACTION ALGO ---
            # Pichli 20 candles ka sabse Low (Support) aur sabse High (Resistance)
            df['Support'] = df['Low'].rolling(window=20).min().shift(1)
            df['Resistance'] = df['High'].rolling(window=20).max().shift(1)
            df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

            total_signals, target_hit, sl_hit, pending = 0, 0, 0, 0
            st.success("✅ Support/Resistance Zones Loaded! Scanning...")
            st.subheader("📊 Price Action Trade Results:")
            
            start_index = max(25, len(df) - 400) 
            
            for i in range(start_index, len(df) - 1): 
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                body = abs(curr['Close'] - curr['Open'])
                lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
                upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
                
                pattern_time = df.index[i].strftime("%Y-%m-%d %H:%M")
                pattern, trade_type, entry, sl, target = "", "", 0, 0, 0
                
                # Zone Checks (Price Zameen ya Chhat ke 0.5% ke andar hona chahiye)
                is_near_support = curr['Low'] <= (curr['Support'] * 1.005)
                is_near_resistance = curr['High'] >= (curr['Resistance'] * 0.995)
                is_high_volume = curr['Volume'] > curr['Vol_MA20'] # Volume average se zyada
                
                # 🟢 BUY RULE: Support ke paas + High Volume
                if is_near_support and is_high_volume: 
                    # 1. Hammer at Support
                    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and curr['Close'] > prev['Close']:
                        pattern, trade_type = "🔨 Hammer @ Support", "BUY"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 1.00 # Buffer for Operator SL Hunting
                        target = entry + (1.5 * abs(entry - sl))
                        
                    # 2. Bullish Engulfing at Support
                    elif (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
                         (curr['Open'] <= prev['Close']) and (curr['Close'] >= prev['Open']):
                        pattern, trade_type = "🔥 Bull Engulf @ Support", "BUY"
                        entry = curr['High'] + 0.50
                        sl = curr['Low'] - 1.00
                        target = entry + (1.5 * abs(entry - sl))

                # 🔴 SELL RULE: Resistance ke paas + High Volume
                if is_near_resistance and is_high_volume:
                    # 3. Shooting Star at Resistance
                    if upper_wick > (2 * body) and lower_wick < (0.5 * body) and curr['Close'] < prev['Close']:
                        pattern, trade_type = "☄️ Shooting Star @ Resist", "SELL"
                        entry = curr['Low'] - 0.50
                        sl = curr['High'] + 1.00 # Buffer
                        target = entry - (1.5 * abs(entry - sl))
                        
                    # 4. Bearish Engulfing at Resistance
                    elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and \
                         (curr['Open'] >= prev['Close']) and (curr['Close'] <= prev['Open']):
                        pattern, trade_type = "🩸 Bear Engulf @ Resist", "SELL"
                        entry = curr['Low'] - 0.50
                        sl = curr['High'] + 1.00
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
                st.info(f"🏆 Maddy Price Action Win Rate: {round(win_rate, 2)}%")
                if win_rate >= 50: st.balloons()
            else:
                st.info("😎 No trades at zones today. Capital protected!")
                
