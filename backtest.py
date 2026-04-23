import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Maddy AI Master Engine", layout="wide")
st.title("🦅 Maddy AI: The Ultimate Master Dashboard")
st.write("Intraday (6-Point) ⚡ + Swing (5-Point) 🚀 Analysis Active!")

watchlist = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", 
    "KOTAKBANK.NS", "BAJAJFINSV.NS", "SHRIRAMFIN.NS", "CHOLAFIN.NS", "JIOFIN.NS", 
    "HDFCLIFE.NS", "SBILIFE.NS", "ICICIGI.NS", "ICICIPRULI.NS", "HDFCAMC.NS", 
    "SBICARD.NS", "LICI.NS", "MUTHOOTFIN.NS", "INDUSINDBK.NS", "BANKBARODA.NS", 
    "CANBK.NS", "UNIONBANK.NS", "PNB.NS", "RECLTD.NS", "PFC.NS", 
    "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", 
    "OFSS.NS", "PERSISTENT.NS", "COFORGE.NS", 
    "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS", 
    "BPCL.NS", "IOC.NS", "GAIL.NS", 
    "ADANIGREEN.NS", "ADANIPOWER.NS", "ADANIENSOL.NS", "JSWENERGY.NS", "TATAPOWER.NS", 
    "MARUTI.NS", "M&M.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", 
    "TVSMOTOR.NS", "HEROMOTOCO.NS", "MOTHERSON.NS", "BOSCHLTD.NS", 
    "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TITAN.NS", 
    "DMART.NS", "GODREJCP.NS", "MARICO.NS", "DABUR.NS", "VBL.NS", "MCDOWELL-N.NS", 
    "PIDILITIND.NS", "COLPAL.NS", "BERGEPAINT.NS", "ASIANPAINT.NS", "TRENT.NS"
]

    "TITAN.NS", "POLICYBZR.NS", "LODHA.NS", 
    "TATAPOWER.NS", "ADANIPORTS.NS", "RELIANCE.NS", 
    "HDFCBANK.NS", "INDOTECH.NS", "STLTECH.NS", "LUXIND.NS", "TRENT.NS", 
    "TATACHEM.NS", "RELIANCE.NS", "CIPLA.NS", "HDFCBANK.NS", "SBIN.NS"
]

if st.button("🚨 Run Full Market Analysis"):
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚡ INTRADAY RADAR (15-Min)")
    with col2:
        st.subheader("🚀 SWING RADAR (1-Day)")
        
    intraday_found = False
    swing_found = False
    
    # Global Sector Sync (Pehle Nifty ka mood check karo)
    with st.spinner("⏳ Scanning Market Mood (Nifty50)..."):
        try:
            nifty = yf.download("^NSEI", period="5d", interval="1d", progress=False)
            nifty_change = ((nifty.iloc[-1]['Close'] - nifty.iloc[-2]['Close']) / nifty.iloc[-2]['Close']) * 100
            nifty_mood = "POSITIVE" if nifty_change > 0 else "NEGATIVE"
        except:
            nifty_mood = "NEUTRAL"

    progress_bar = st.progress(0)
    
    for i, stock in enumerate(watchlist):
        try:
            # ---------------------------------------------------------
            # FETCH DAILY DATA (For Swing & Intraday HTF Trend)
            # ---------------------------------------------------------
            df_daily = yf.download(stock, period="1y", interval="1d", progress=False)
            if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.droplevel(1)
            df_daily = df_daily.dropna()
            
            # Daily Indicators
            df_daily['EMA_50'] = df_daily['Close'].ewm(span=50, adjust=False).mean()
            df_daily['EMA_200'] = df_daily['Close'].ewm(span=200, adjust=False).mean()
            df_daily['52W_High'] = df_daily['High'].rolling(window=200).max().shift(1)
            df_daily['Vol_MA20'] = df_daily['Volume'].rolling(window=20).mean().shift(1)
            
            today_d = df_daily.iloc[-1]
            
            # --- SWING ANALYSIS (5-Point Checklist) ---
            s_trend = today_d['Close'] > today_d['EMA_50'] and today_d['EMA_50'] > today_d['EMA_200']
            s_breakout = today_d['Close'] > today_d['52W_High']
            s_volume = today_d['Volume'] > (1.5 * today_d['Vol_MA20'])
            s_sector = nifty_mood == "POSITIVE"
            
            if s_breakout and s_volume: # Agar Breakout aur Volume hai, toh hi checklist dikhao
                with col2:
                    st.success(f"🔥 **[SWING ROCKET]** {stock}")
                    st.write(f"✅ Rule 1: Trend is UP" if s_trend else "❌ Rule 1: Trend is Weak")
                    st.write(f"✅ Rule 2: 52-Week Breakout")
                    st.write(f"✅ Rule 3: Operator Volume Found")
                    st.write(f"✅ Rule 4: Sector Sync (Nifty Pos)" if s_sector else "⚠️ Rule 4: Sector Not Sync")
                    
                    if s_trend and s_sector:
                        tgt = today_d['Close'] * 1.20
                        sl = today_d['Close'] * 0.93
                        st.info(f"🛡️ Rule 5 (Risk/Reward): Entry ₹{round(today_d['Close'],2)} | TGT ₹{round(tgt,2)} | Deep SL ₹{round(sl,2)}")
                    swing_found = True

            # ---------------------------------------------------------
            # FETCH 15-MIN DATA (For Intraday)
            # ---------------------------------------------------------
            df_15m = yf.download(stock, period="1mo", interval="15m", progress=False)
            if isinstance(df_15m.columns, pd.MultiIndex): df_15m.columns = df_15m.columns.droplevel(1)
            df_15m = df_15m.dropna()
            
            # Intraday Indicators
            df_15m['VWAP'] = (df_15m['Close'] * df_15m['Volume']).cumsum() / df_15m['Volume'].cumsum()
            df_15m['Support_100'] = df_15m['Low'].rolling(window=100).min().shift(1)
            
            today_15m = df_15m.iloc[-1]
            
            # --- INTRADAY ANALYSIS (6-Point Checklist) ---
            i_htf_trend = today_d['Close'] > today_d['EMA_200'] # Rule 1: Higher Time Frame
            i_sector = nifty_mood == "POSITIVE"                 # Rule 2: Sector Sync
            i_vwap = today_15m['Close'] > today_15m['VWAP']     # Rule 3: Above VWAP
            i_zone = today_15m['Low'] <= (today_15m['Support_100'] * 1.003) # Rule 4: At Support
            
            if i_zone: # Agar stock support par aaya hai, tabhi checklist verify karo
                with col1:
                    st.info(f"🟢 **[INTRADAY SCAN]** {stock} at Support")
                    st.write(f"✅ Rule 1: Daily Trend UP" if i_htf_trend else "❌ Rule 1: Daily Trend Down")
                    st.write(f"✅ Rule 2: Nifty Sector Sync" if i_sector else "⚠️ Rule 2: Nifty Negative")
                    st.write(f"✅ Rule 3: Price > VWAP" if i_vwap else "❌ Rule 3: Below VWAP (Weak)")
                    st.write(f"✅ Rule 4: At Concrete Support")
                    
                    if i_htf_trend and i_sector and i_vwap:
                        st.success(f"🎯 **PRO SETUP MATCHED!** Entry: ₹{round(today_15m['Close'], 2)}")
                    intraday_found = True
                    
        except Exception as e:
            pass # Skip on error
            
        progress_bar.progress((i + 1) / len(watchlist))

    st.divider()
    if not intraday_found:
        with col1: st.warning("😎 Intraday: Koi bhi stock Concrete Support par nahi hai.")
    if not swing_found:
        with col2: st.warning("😎 Swing: Aaj kisi stock ne chhat nahi todi.")
            
