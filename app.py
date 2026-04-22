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
    
