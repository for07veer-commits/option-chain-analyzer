import requests
import pandas as pd
import streamlit as st

st.title("⚡ Live NSE Option Chain Analyzer & Smart Signals")

# 1. Dropdown for Index Selection
selected_index = st.selectbox("🔍 Select Index to Analyze:", ["NIFTY", "BANKNIFTY", "FINNIFTY"])

# Sidebar for Days to Expiry
days_to_expiry = st.sidebar.number_input("Days to Expiry (DTE):", min_value=0, max_value=30, value=5)

# 2. NSE se Real-time Data Fetch Karne ka Function
def fetch_nse_option_chain(symbol):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = requests.Session()
    
    try:
        # Step 1: Cookies lene ke liye main page hit karo
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        # Step 2: Option chain data lo
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"NSE Connection Error: Status Code {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to NSE: {e}")
        return None

# 3. JSON Data ko Process Karke DataFrame Banana
def process_nse_data(json_data):
    if not json_data:
        return None, 0
        
    records = json_data['records']['data']
    spot_price = json_data['records']['underlyingValue']
    
    processed_data = []
    for item in records:
        strike = item.get('strikePrice')
        
        ce = item.get('CE', {})
        call_oi = ce.get('openInterest', 0)
        call_ltp_change = ce.get('pChange', 0)
        
        pe = item.get('PE', {})
        put_oi = pe.get('openInterest', 0)
        put_ltp_change = pe.get('pChange', 0)
        
        processed_data.append({
            'Strike Price': strike,
            'Call_OI': call_oi,
            'Call_LTP_Change_%': call_ltp_change,
            'Put_OI': put_oi,
            'Put_LTP_Change_%': put_ltp_change
        })
        
    df = pd.DataFrame(processed_data)
    return df, spot_price

# 4. Smart Money Rejection & BUY Signal Logic
def detect_smart_money_rejection(df, days_to_expiry):
    alerts = []
    for index, row in df.iterrows():
        alert_msg = "No Action"
        if row['Put_LTP_Change_%'] <= -50 and row['Put_OI'] > 1000 and days_to_expiry >= 1:
            alert_msg = "🟢 BUY CALL (Support Rejection)"
        elif row['Call_LTP_Change_%'] <= -50 and row['Call_OI'] > 1000 and days_to_expiry >= 1:
            alert_msg = "🔴 BUY PUT (Resistance Rejection)"
        alerts.append(alert_msg)
    df['Action_Signal'] = alerts
    return df

# 5. App Execution
if st.button("🔄 Fetch Live NSE Data"):
    with st.spinner("Fetching live market data from NSE..."):
        raw_json = fetch_nse_option_chain(selected_index)
        if raw_json:
            df, spot_price = process_nse_data(raw_json)
            
            # Spot price ke paas wale strikes filter karein (± 400 points)
            df_filtered = df[(df['Strike Price'] >= spot_price - 400) & (df['Strike Price'] <= spot_price + 400)]
            
            # Signals run karein
            analyzed_df = detect_smart_money_rejection(df_filtered, days_to_expiry)
            
            st.success(f"Data Loaded Successfully! Current Spot Price: {spot_price}")
            
            # Highlight function
            def highlight_buy_signals(row):
                if 'BUY CALL' in row['Action_Signal']:
                    return ['background-color: rgba(0, 255, 0, 0.2); color: #006400; font-weight: bold'] * len(row)
                elif 'BUY PUT' in row['Action_Signal']:
                    return ['background-color: rgba(255, 0, 0, 0.2); color: #8B0000; font-weight: bold'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(analyzed_df.style.apply(highlight_buy_signals, axis=1), use_container_width=True)
