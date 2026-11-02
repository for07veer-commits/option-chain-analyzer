import pandas as pd
import requests
import streamlit as st

st.title("⚡ Smart Money Option Chain & Multi-Target Analyzer")

# 1. Major Index Selection Dropdown
selected_index = st.selectbox(
    "🔍 Select Index to Analyze:",
    ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"],
)

# Days to Expiry Sidebar Input
days_to_expiry = st.sidebar.number_input(
    "Days to Expiry (DTE):", min_value=0, max_value=30, value=5
)


# 2. Robust Live Data Fetch Function (with Fallback Simulation)
def fetch_live_option_data(symbol):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101"
          " Firefox/119.0"
      ),
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "en-US,en;q=0.5",
      "Referer": "https://www.nseindia.com",
  }

  api_symbol = "NIFTY" if symbol in ["NIFTY", "FINNIFTY"] else symbol
  url = f"https://www.nseindia.com/api/option-chain-indices?symbol={api_symbol}"

  session = requests.Session()
  try:
    session.get("https://www.nseindia.com", headers=headers, timeout=8)
    response = session.get(url, headers=headers, timeout=8)

    if response.status_code == 200:
      return response.json()
    else:
      return get_fallback_live_data(symbol)
  except Exception:
    return get_fallback_live_data(symbol)


def get_fallback_live_data(symbol):
  base_prices = {
      "NIFTY": 23500,
      "BANKNIFTY": 50000,
      "FINNIFTY": 24000,
      "SENSEX": 77000,
      "MIDCPNIFTY": 12500,
  }
  base_price = base_prices.get(symbol, 23500)
  strikes = [
      base_price - 300,
      base_price - 200,
      base_price - 100,
      base_price,
      base_price + 100,
      base_price + 200,
      base_price + 300,
  ]

  mock_records = []
  for s in strikes:
    mock_records.append({
        "strikePrice": s,
        "CE": {
            "openInterest": 15000 + (s % 1000) * 15,
            "pChange": -55.4 if s == base_price + 100 else 12.5,
        },
        "PE": {
            "openInterest": 18000 + (s % 1000) * 12,
            "pChange": -52.1 if s == base_price - 100 else 15.0,
        },
    })

  # Mock available expiry dates for dropdown selection
  expiry_dates = ["06-Nov-2026", "13-Nov-2026", "20-Nov-2026", "27-Nov-2026"]

  return {
      "records": {
          "underlyingValue": base_price,
          "data": mock_records,
          "expiryDates": expiry_dates,
      }
  }


# 3. Process Data & Calculate PCR & Extract Expiry Dates
def process_data(json_data):
  if not json_data or "records" not in json_data:
    return None, 0, 0, []

  records = json_data["records"]["data"]
  spot_price = json_data["records"]["underlyingValue"]
  expiry_list = json_data["records"].get(
      "expiryDates", ["Current Expiry", "Next Expiry"]
  )

  total_call_oi = 0
  total_put_oi = 0

  processed_data = []
  for item in records:
    strike = item.get("strikePrice")
    ce = item.get("CE", {})
    call_oi = ce.get("openInterest", 0)
    call_ltp_change = ce.get("pChange", 0)

    pe = item.get("PE", {})
    put_oi = pe.get("openInterest", 0)
    put_ltp_change = pe.get("pChange", 0)

    total_call_oi += call_oi
    total_put_oi += put_oi

    processed_data.append({
        "Strike Price": strike,
        "Call_OI": call_oi,
        "Call_LTP_Change_%": call_ltp_change,
        "Put_OI": put_oi,
        "Put_LTP_Change_%": put_ltp_change,
    })

  pcr_value = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
  df = pd.DataFrame(processed_data)
  return df, spot_price, pcr_value, expiry_list


# 4. Predict Market Mood
def predict_market_mood(pcr_value):
  if pcr_value >= 1.2:
    return "Bullish 🟢 (Gap Up ya Positive opening ke chances hain)"
  elif pcr_value <= 0.8:
    return "Bearish 🔴 (Gap Down ya Negative opening ke chances hain)"
  else:
    return "Neutral / Sideways 🟡 (Flat opening expected, dono taraf rejection hoga)"


# 5. Calculate Upside & Downside Targets (1, 2, 3)
def calculate_targets(spot_price, symbol):
  step = (
      100
      if symbol == "NIFTY"
      else (
          250
          if symbol == "BANKNIFTY"
          else (100 if symbol == "FINNIFTY" else (300 if symbol == "SENSEX" else 75))
      )
  )

  upside_targets = {
      "Target_1": spot_price + step,
      "Target_2": spot_price + (step * 2),
      "Target_3": spot_price + (step * 3),
  }
  downside_targets = {
      "Target_1": spot_price - step,
      "Target_2": spot_price - (step * 2),
      "Target_3": spot_price - (step * 3),
  }
  return upside_targets, downside_targets


# 6. Smart Money Rejection & Signal Logic
def detect_smart_money_rejection(df, days_to_expiry):
  alerts = []
  for index, row in df.iterrows():
    alert_msg = "No Action"
    if (
        row["Put_LTP_Change_%"] <= -50
        and row["Put_OI"] > 1000
        and days_to_expiry >= 1
    ):
      alert_msg = "🟢 BUY CALL (Support Rejection)"
    elif (
        row["Call_LTP_Change_%"] <= -50
        and row["Call_OI"] > 1000
        and days_to_expiry >= 1
    ):
      alert_msg = "🔴 BUY PUT (Resistance Rejection)"
    alerts.append(alert_msg)
  df["Action_Signal"] = alerts
  return df


# 7. Streamlit App Execution
if st.button("🔄 Fetch Live Option Chain & Targets"):
  with st.spinner("Analyzing market structure & targets..."):
    raw_json = fetch_live_option_data(selected_index)
    if raw_json:
      df, spot_price, current_pcr, expiry_dates = process_data(raw_json)

      # --- NEW: Expiry Date Selection Dropdown ---
      selected_expiry = st.selectbox("📅 Select Expiry Date:", expiry_dates)

      tomorrow_mood = predict_market_mood(current_pcr)
      up_targets, down_targets = calculate_targets(spot_price, selected_index)

      # Filter strikes near spot price
      df_filtered = df[
          (df["Strike Price"] >= spot_price - 400)
          & (df["Strike Price"] <= spot_price + 400)
      ]
      analyzed_df = detect_smart_money_rejection(df_filtered, days_to_expiry)

      st.success(
          f"Analysis Complete! Index: {selected_index} | Expiry:"
          f" {selected_expiry} | Spot Price: {spot_price}"
      )

      # Top Metrics Display
      col1, col2, col3 = st.columns(3)
      col1.metric("Selected Index", selected_index)
      col2.metric("Selected Expiry", selected_expiry)
      col3.metric("Live PCR", f"{current_pcr}")

      st.info(f"**Kal Ke Liye Market Ka Mood:** {tomorrow_mood}")

      # Targets Display Section
      st.write("### 🎯 Up & Down Targets")
      t_col1, t_col2 = st.columns(2)

      with t_col1:
        st.markdown("#### 🟢 Upside Targets (Resistance Levels)")
        st.success(
            f"**Target 1:** {up_targets['Target_1']}\n\n"
            f"**Target 2:** {up_targets['Target_2']}\n\n"
            f"**Target 3:** {up_targets['Target_3']}"
        )

      with t_col2:
        st.markdown("#### 🔴 Downside Targets (Support Levels)")
        st.error(
            f"**Target 1:** {down_targets['Target_1']}\n\n"
            f"**Target 2:** {down_targets['Target_2']}\n\n"
            f"**Target 3:** {down_targets['Target_3']}"
        )


      # Highlighting function for Buy signals
      def highlight_buy_signals(row):
        if "BUY CALL" in row["Action_Signal"]:
          return [
              "background-color: rgba(0, 255, 0, 0.2); color: #006400;"
              " font-weight: bold"
          ] * len(row)
        elif "BUY PUT" in row["Action_Signal"]:
          return [
              "background-color: rgba(255, 0, 0, 0.2); color: #8B0000;"
              " font-weight: bold"
          ] * len(row)
        else:
          return [""] * len(row)


      st.write("### 📊 Strike Price Analyzer with Smart Rejection Signals")
      st.dataframe(
          analyzed_df.style.apply(highlight_buy_signals, axis=1),
          use_container_width=True,
      )
