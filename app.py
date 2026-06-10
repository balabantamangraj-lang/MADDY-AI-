# Memory Setup
if 'alerted_today' not in st.session_state:
    st.session_state.alerted_today = {}

# Indicators
rsi = ta.rsi(df['Close']).iloc[-1]

ema50 = ta.ema(df['Close'], length=50).iloc[-1]
ema200 = ta.ema(df['Close'], length=200).iloc[-1]

vol_current = df['Volume'].iloc[-1]
vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

# Accuracy Score
score = 0

if ema50 > ema200:
    score += 25

if rsi > 55:
    score += 25

if vol_current > (vol_avg * 1.5):
    score += 25

if price > vwap_current:
    score += 25

st.progress(score / 100)
st.write(f"Confidence Score: {score}%")

# Duplicate Alert Protection
alert_key = f"{stock}_{pattern_name}_{date.today()}"

if is_valid_trade:
    st.success(f"🎯 PRO SETUP: {pattern_name}")
    st.write(f"{trade_type}: ₹{round(entry_price,2)}")
    st.write(f"🛑 SL: ₹{round(sl_price,2)}")
    st.write(f"📈 Target: ₹{round(target_price,2)}")

    if alert_key not in st.session_state.alerted_today:
        send_telegram_alert(msg)
        st.session_state.alerted_today[alert_key] = True
