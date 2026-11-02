import pandas as pd
import streamlit as st

# 1. Smart Money & "BUY" Signal Logic
def detect_smart_money_rejection(df, days_to_expiry):
    alerts = []
    for index, row in df.iterrows():
        alert_msg = "No Action"
        
        # Agar Put premium 50% se zyada gira hai, par OI strong hai -> Support banega -> Market upar jayega
        if row['Put_LTP_Change_%'] <= -50 and row['Put_OI'] > 10 and days_to_expiry >= 1:
            alert_msg = "🟢 BUY CALL (Support Rejection)"
            
        # Agar Call premium 50% se zyada gira hai, par OI strong hai -> Resistance banega -> Market niche girega
        elif row['Call_LTP_Change_%'] <= -50 and row['Call_OI'] > 10 and days_to_expiry >= 1:
            alert_msg = "🔴 BUY PUT (Resistance Rejection)"
            
        alerts.append(alert_msg)
        
    df['Action_Signal'] = alerts
    return df

# 2. Kal ka Market Mood (Tomorrow's Prediction) Calculate Karna
def predict_market_mood(pcr_value):
    if pcr_value >= 1.2:
        return "Bullish 🟢 (Kal Gap Up ya Positive opening ke chances hain)"
    elif pcr_value <= 0.8:
        return "Bearish 🔴 (Kal Gap Down ya Negative opening ke chances hain)"
    else:
        return "Neutral / Sideways 🟡 (Flat opening expected, dono taraf rejection hoga)"

# ----------------- STREAMLIT APP UI -----------------

st.title("Smart Money Option Chain & BUY Signal Analyzer")

# 1. Index Dropdown Menu
selected_index = st.selectbox("🔍 Select Index to Analyze:", 
                              ["NIFTY 50", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"])

# 2. Days to Expiry 
st.sidebar.header("Expiry Settings")
days_to_expiry = st.sidebar.number_input("Days to Expiry (DTE):", min_value=0, max_value=30, value=8)

st.write(f"### Analyzing: {selected_index}")

# Live market PCR 
current_pcr = 0.97 
tomorrow_mood = predict_market_mood(current_pcr)

# 3. Top Metrics: DTE aur Market Mood dikhana
col1, col2, col3 = st.columns(3)
col1.metric("Selected Index", selected_index)
col2.metric("Days to Expiry", f"{days_to_expiry} Days")
col3.metric("Live PCR", f"{current_pcr}")

st.info(f"**Kal Ke Liye Market Ka Mood:** {tomorrow_mood}")

# 4. Sample Data 
data = {
    'Strike Price': [23300, 23350, 23400, 23450, 23500],
    'Call_OI': [20.65, 7.31, 13.59, 4.18, 23.40], 
    'Call_LTP_Change_%': [-55.13, -52.82, -51.73, -49.69, -48.78],
    'Put_OI': [17.05, 6.85, 7.98, 1.25, 5.54],     
    'Put_LTP_Change_%': [118.23, 125.05, 132.35, 141.04, 144.37]
}

df = pd.DataFrame(data)

# Logic Run Karein
analyzed_df = detect_smart_money_rejection(df, days_to_expiry)

# ---------------- HIGHLIGHT "BUY" LOGIC ----------------
def highlight_buy_signals(row):
    if 'BUY CALL' in row['Action_Signal']:
        return ['background-color: rgba(0, 255, 0, 0.2); color: #006400; font-weight: bold'] * len(row)
    elif 'BUY PUT' in row['Action_Signal']:
        return ['background-color: rgba(255, 0, 0, 0.2); color: #8B0000; font-weight: bold'] * len(row)
    else:
        return [''] * len(row)

st.write("### 📊 Strike Price Analyzer with Action Signals")
st.write("Jahan smart money ki wajah se reversal aayega, wahan sidhe **BUY CALL** ya **BUY PUT** likha aayega.")

st.dataframe(analyzed_df.style.apply(highlight_buy_signals, axis=1), use_container_width=True)
