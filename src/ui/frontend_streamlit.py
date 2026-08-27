# File: src/ui/frontend_streamlit.py
import time
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="BAS HAR Assistant - On-board Dashboard",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 BAS HAR Assistant — Bharatiya Antariksha Station")
st.subheader("Offline On-board Human Activity Recognition & Protocol Monitor")

# Sidebar Controls
st.sidebar.header("🕹️ Experiment Controls")

def fetch_status():
    try:
        resp = requests.get(f"{BACKEND_URL}/status", timeout=2.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.sidebar.error(f"Cannot connect to backend: {e}")
    return None

def fetch_logs():
    try:
        resp = requests.get(f"{BACKEND_URL}/log?limit=15", timeout=2.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []

if st.sidebar.button("🔄 Reset Experiment"):
    try:
        requests.post(f"{BACKEND_URL}/reset")
        st.sidebar.success("Experiment state reset successfully!")
    except Exception as e:
        st.sidebar.error(f"Failed to reset: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Manual Step Trigger (Demo)")

steps_list = ["S1", "S2", "S3", "S4", "S5", "S6"]
selected_step = st.sidebar.selectbox("Select Step to Simulate", steps_list)
if st.sidebar.button(f"Trigger Step {selected_step}"):
    try:
        res = requests.post(f"{BACKEND_URL}/trigger_step", json={"step_id": selected_step, "confidence": 0.95})
        st.sidebar.info(f"Triggered {selected_step}: {res.json().get('alert_type')}")
    except Exception as e:
        st.sidebar.error(f"Error triggering step: {e}")

status_data = fetch_status()

if status_data:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Step", status_data.get("current_step_id", "N/A"))
    with col2:
        next_steps = ", ".join(status_data.get("next_allowed_steps", []))
        st.metric("Allowed Next Step(s)", next_steps if next_steps else "None")
    with col3:
        st.metric("Confidence", f"{status_data.get('confidence', 0.0)*100:.1f}%")
    with col4:
        alert = status_data.get("last_alert", "OK")
        st.metric("Alert Status", alert)

    # Alert Display Banner
    alert_type = status_data.get("last_alert", "OK")
    msg = status_data.get("last_message", "")

    if alert_type in ["OK", "REPEATED"]:
        st.success(f"✅ State Status: {alert_type} — {msg}")
    elif alert_type == "COMPLETED":
        st.balloons()
        st.success(f"🎉 Experiment Completed Successfully! {msg}")
    elif alert_type in ["SKIPPED", "WRONG_ORDER"]:
        st.warning(f"⚠️ Sequence Alert ({alert_type}): {msg}")
    else:
        st.error(f"🚨 Critical Alert ({alert_type}): {msg}")

    # Current Step Details Card
    st.markdown("### 📋 Protocol Details")
    st.info(f"**Step Name**: {status_data.get('current_step_name', '')}\n\n"
            f"**Description**: {status_data.get('current_step_description', '')}")

    # Logs Table
    st.markdown("### 📜 Real-time Event Log")
    logs_data = fetch_logs()
    if logs_data:
        st.dataframe(logs_data, use_container_width=True)
    else:
        st.write("No events logged yet.")

else:
    st.warning("⚠️ FastAPI Backend is not running. Please start `python main.py` first.")

# Auto-refresh loop
time.sleep(2)
st.rerun()
