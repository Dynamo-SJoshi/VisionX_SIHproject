# File: src/ui/frontend_streamlit.py
"""
BAS AI Copilot — On-Board Mission Control Dashboard
Bharatiya Antariksha Station (BAS) Human Activity Recognition & Digital Copilot

Designed for edge deployment on space station payload hardware and ground station telemetry.
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

from src.ui.components.alerts import render_decision_banner
from src.ui.components.timeline import render_step_timeline
from src.ui.components.protocol import render_next_action_card
from src.ui.components.status import render_system_health, render_rack_spatial_hud

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

BACKEND_URL = os.environ.get("BAS_BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="BAS AI Copilot — Mission Control",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# SPACE STATION MISSION CONTROL DARK THEME STYLING
# ============================================================================

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, .font-mono {
        font-family: 'JetBrains Mono', monospace;
    }

    /* Main background & glassmorphism */
    .stApp {
        background-color: #0b0f19;
        background-image: 
            radial-gradient(at 0% 0%, rgba(14, 165, 233, 0.08) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.05) 0px, transparent 50%);
        color: #f1f5f9;
    }

    /* Header styling */
    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid #1e293b;
        border-radius: 12px;
        backdrop-filter: blur(12px);
        margin-bottom: 20px;
    }

    .main-header h1 {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .main-header span.tag {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 9999px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* Card containers */
    .mc-card {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        backdrop-filter: blur(8px);
        margin-bottom: 16px;
    }

    /* Metric card overrides */
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Buttons styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        transition: all 0.2s ease-in-out;
        border: 1px solid #334155;
    }
    .stButton>button:hover {
        border-color: #38bdf8;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }
</style>
"""

if hasattr(st, "html"):
    st.html(CUSTOM_CSS)
else:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# API CLIENT HELPER FUNCTIONS
# ============================================================================

def api_get(endpoint: str, timeout: float = 2.0) -> Optional[Any]:
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def api_post(endpoint: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 3.0) -> Optional[Any]:
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", json=payload or {}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.sidebar.error(f"API Request Failed ({endpoint}): {e}")
    return None


# ============================================================================
# MOCK TELEMETRY (FALLBACK WHEN BACKEND IS OFFLINE)
# ============================================================================

def get_mock_telemetry() -> Dict[str, Any]:
    return {
        "timestamp": time.time(),
        "session_id": "SIM_DEMO_EXP_001",
        "experiment_name": "Sample Liquid Transfer Protocol",
        "fps": 29.8,
        "status": "NORMAL",
        "current_step": {
            "id": "S3",
            "title": "Open Sample Tube Cap",
            "expected_action": "open",
            "state": "IN_PROGRESS",
        },
        "next_step": {"id": "S4", "title": "Transfer Liquid Specimen"},
        "progress_percentage": 50.0,
        "protocol_steps": [
            {"id": "S1", "title": "Identify Target Sample Tube", "status": "COMPLETED", "allowed_next": ["S2"]},
            {"id": "S2", "title": "Pick Sample Tube", "status": "COMPLETED", "allowed_next": ["S3"]},
            {"id": "S3", "title": "Open Sample Tube Cap", "status": "ACTIVE", "allowed_next": ["S4"]},
            {"id": "S4", "title": "Transfer Liquid Specimen", "status": "PENDING", "allowed_next": ["S5"]},
            {"id": "S5", "title": "Seal Sample Tube Cap", "status": "PENDING", "allowed_next": ["S6"]},
            {"id": "S6", "title": "Place Tube in Payload Rack", "status": "PENDING", "allowed_next": []},
        ],
        "last_decision": {
            "type": "VALID",
            "action": "open",
            "confidence": 0.96,
            "rack_zone": "WORKBENCH",
            "explanation": "Sample tube cap opened nominal in designated workbench area.",
            "voice_message": "Tube opened successfully. Prepare micropipette for transfer.",
            "evidence_snapshot_url": None,
        },
        "system_health": {
            "camera": "CONNECTED (EDGE SIM)",
            "edge_inference": "ACTIVE",
            "protocol_engine": "STATE MACHINE RUNNING",
        },
    }


# ============================================================================
# SIDEBAR: MISSION CONTROLS & DEMO INTERACTION
# ============================================================================

sidebar_controls_html = """
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
    <span style="font-size: 24px;">🕹️</span>
    <h2 style="margin: 0; font-size: 18px; font-weight: 700; color: #f8fafc;">Mission Controls</h2>
</div>
"""
if hasattr(st.sidebar, "html"):
    st.sidebar.html(sidebar_controls_html)
else:
    st.sidebar.markdown(sidebar_controls_html, unsafe_allow_html=True)

# Backend Status Indicator
health_info = api_get("/api/v1/health")
backend_online = health_info is not None

if backend_online:
    st.sidebar.success("🟢 Edge Backend Online")
else:
    st.sidebar.warning("🟡 Backend Offline (Demo Simulation Active)")

st.sidebar.markdown("---")

# 1. Session Control Panel
st.sidebar.subheader("📡 Flight Session")
col_s1, col_s2 = st.sidebar.columns(2)

astronaut_id = st.sidebar.text_input("Astronaut Call-sign", value="ASTRO_SHARMA_01")
session_id_input = st.sidebar.text_input("Session Identifier", value=f"EXP_{int(time.time()) % 100000}")

with col_s1:
    if st.button("▶ Start Session", width="stretch"):
        res = api_post(
            "/api/v1/session/start",
            {"session_id": session_id_input, "astronaut_id": astronaut_id, "experiment_id": "sample_transfer_v1"},
        )
        if res:
            st.sidebar.success(f"Session {session_id_input} Started!")
            st.rerun()

with col_s2:
    if st.button("⏹ Stop Session", width="stretch"):
        res = api_post("/api/v1/session/stop")
        if res:
            st.sidebar.info("Session Stopped.")
            st.rerun()

st.sidebar.markdown("---")

# 2. Dynamic Protocol Hot-Swapping (Judge Differentiator)
st.sidebar.subheader("🔄 Protocol Hot-Swapping")
protocol_options = {
    "Astronaut & Mobile Inspection v1": "data/configs/astronaut_mobile_protocol_v1.json",
    "Sample Liquid Transfer v1": "data/configs/sample_transfer_protocol_v1.json",
    "Protein Crystallization v2": "data/configs/sample_experiment_v2.json",
}
selected_protocol_label = st.sidebar.selectbox("Select Experiment Protocol", list(protocol_options.keys()))
selected_config_path = protocol_options[selected_protocol_label]


col_p1, col_p2 = st.sidebar.columns(2)
with col_p1:
    if st.button("⚡ Hot-Swap", width="stretch"):
        res = api_post("/api/v1/protocol/load", {"config_file_path": selected_config_path})
        if res:
            st.sidebar.success(f"Loaded: {res.get('message', 'Protocol active')}")
            st.rerun()

with col_p2:
    if st.button("🔁 Reset State", width="stretch"):
        res = api_post("/api/v1/protocol/reset")
        if res:
            st.sidebar.info("Reset to initial step.")
            st.rerun()

st.sidebar.markdown("---")

# 3. Manual Operator / Astronaut Confirmation (Uncertainty Fallback)
st.sidebar.subheader("✋ Operator Override")
step_to_confirm = st.sidebar.text_input("Step ID to Confirm", value="S3")
if st.sidebar.button("✅ Confirm Step Execution", width="stretch"):
    res = api_post("/api/v1/confirm", {"step_id": step_to_confirm, "astronaut_id": astronaut_id})
    if res:
        st.sidebar.success(f"Confirmed step {step_to_confirm}!")
        st.rerun()

st.sidebar.markdown("---")

# 4. Live Action Simulator for Presentations & Judges
st.sidebar.subheader("🎯 Demo Action Simulator")
sim_action = st.sidebar.selectbox("Action Type", ["identify", "pick", "open", "transfer", "seal", "place"])
sim_zone = st.sidebar.selectbox("Rack Zone", ["A1", "A2", "B1", "B2", "C1", "C2", "WORKBENCH"])
sim_conf = st.sidebar.slider("Detection Confidence", 0.40, 1.0, 0.95, 0.05)

col_demo1, col_demo2 = st.sidebar.columns(2)
with col_demo1:
    if st.button("🚀 Trigger Action", width="stretch"):
        action_payload = {
            "event_id": f"evt_sim_{int(time.time() * 1000) % 100000}",
            "session_id": session_id_input,
            "sequence_number": 1,
            "actor_id": astronaut_id,
            "action": sim_action,
            "confidence": sim_conf,
            "status": "VALIDATED" if sim_conf >= 0.70 else "UNVERIFIED",
            "interaction_zone": sim_zone,
            "timestamp": time.time(),
        }
        res = api_post("/api/v1/action", action_payload)
        if res:
            st.sidebar.success(f"Processed: {res.get('decision', {}).get('status', 'OK')}")
            st.rerun()

with col_demo2:
    if st.button("⚠️ Trigger Violation", width="stretch"):
        # Deliberately out-of-order action to showcase procedure violation
        violation_payload = {
            "event_id": f"evt_viol_{int(time.time() * 1000) % 100000}",
            "session_id": session_id_input,
            "sequence_number": 99,
            "actor_id": astronaut_id,
            "action": "place",  # Place tube when it's not even picked or opened
            "confidence": 0.92,
            "status": "VALIDATED",
            "interaction_zone": "C1",
            "timestamp": time.time(),
        }
        res = api_post("/api/v1/action", violation_payload)
        if res:
            st.sidebar.error("Sequence Violation Triggered!")
            st.rerun()

st.sidebar.markdown("---")

# 5. Telemetry Refresh Controls
auto_refresh = st.sidebar.checkbox("Live Telemetry Streaming", value=True)
refresh_rate = st.sidebar.slider("Refresh Interval (seconds)", 1, 5, 2)


# ============================================================================
# MAIN DASHBOARD INTERFACE
# ============================================================================

# Mission Control Header
header_html = """
<div class="main-header">
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 30px;">🛰️</span>
        <div>
            <h1>BAS AI Copilot <span class="tag">Mission Control</span></h1>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
                Bharatiya Antariksha Station (BAS) • Human Activity Recognition & Autonomous Protocol Twin
            </div>
        </div>
    </div>
    <div style="text-align: right;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #38bdf8; font-weight: 700;">
            LOCAL: """ + time.strftime("%H:%M:%S UTC") + """
        </div>
        <div style="font-size: 11px; color: #64748b;">EDGE NODE: BAS-RACK-ALPHA-01</div>
    </div>
</div>
"""
if hasattr(st, "html"):
    st.html(header_html)
else:
    st.markdown(header_html, unsafe_allow_html=True)

# Fetch Latest Telemetry
telemetry = api_get("/api/v1/telemetry") if backend_online else get_mock_telemetry()
if not telemetry:
    telemetry = get_mock_telemetry()

# 1. 3-State Safety & Decision Banner
status = telemetry.get("status", "NORMAL")
last_decision = telemetry.get("last_decision")
render_decision_banner(status=status, last_decision=last_decision)

# System Health Bar
render_system_health(
    system_health=telemetry.get("system_health"),
    fps=telemetry.get("fps", 30.0),
    session_id=telemetry.get("session_id", "UNKNOWN"),
)

if hasattr(st, "html"):
    st.html("<div style='margin-bottom: 18px;'></div>")
else:
    st.markdown("<div style='margin-bottom: 18px;'></div>", unsafe_allow_html=True)

# Main Two-Column Layout
left_col, right_col = st.columns([1.1, 1.0], gap="medium")

# ----------------------------------------------------------------------------
# LEFT COLUMN: Astronaut Guidance, Rack Coordinate HUD & Video Viewport
# ----------------------------------------------------------------------------
with left_col:
    # Next Recommended Action Card
    render_next_action_card(
        current_step=telemetry.get("current_step"),
        next_step=telemetry.get("next_step"),
        protocol_name=telemetry.get("experiment_name", "Active Protocol"),
    )

    # Rack-Relative Spatial Grid HUD
    active_zone = last_decision.get("rack_zone") if last_decision else None
    render_rack_spatial_hud(active_zone=active_zone)

    # Live Camera / Optical Viewport Simulation Card
    st.markdown("#### 📹 Optical Payload Sensor Feed")
    snapshot_url = last_decision.get("evidence_snapshot_url") if last_decision else None

    cam_tab1, cam_tab2, cam_tab3 = st.tabs([
        "🔴 Live Payload Stream",
        "📸 Browser Webcam",
        "🛰️ AR Rack HUD",
    ])

    with cam_tab1:
        if backend_online:
            # Use native MJPEG stream for true real-time video (~30 FPS).
            # The browser handles multipart/x-mixed-replace natively via <img src>,
            # so no Streamlit rerun or Python-side polling is needed.
            mjpeg_url = f"{BACKEND_URL}/api/v1/video/feed"
            mjpeg_html = f"""
            <div style="
                border-radius: 10px;
                overflow: hidden;
                border: 1px solid #334155;
                background: #0b0f19;
                position: relative;
            ">
                <img
                    src="{mjpeg_url}"
                    style="width: 100%; display: block; border-radius: 10px;"
                    alt="Live Detection Feed"
                    onerror="this.style.display='none'; document.getElementById('mjpeg-fallback').style.display='flex';"
                />
                <div id="mjpeg-fallback" style="
                    display: none;
                    height: 300px;
                    align-items: center;
                    justify-content: center;
                    color: #94a3b8;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 13px;
                ">
                    ⚠️ MJPEG stream unavailable — check camera connection
                </div>
                <div style="
                    position: absolute;
                    top: 8px;
                    left: 10px;
                    background: rgba(0,0,0,0.6);
                    color: #ef4444;
                    font-size: 11px;
                    font-weight: 700;
                    font-family: 'JetBrains Mono', monospace;
                    padding: 3px 8px;
                    border-radius: 4px;
                    letter-spacing: 0.5px;
                ">● LIVE</div>
            </div>
            """
            if hasattr(st, "html"):
                st.html(mjpeg_html)
            else:
                st.markdown(mjpeg_html, unsafe_allow_html=True)

            status_cols = st.columns([3, 1])
            with status_cols[0]:
                st.caption("● LIVE — CAM-01 / WORKBENCH | Person & Object Detection Active")
            with status_cols[1]:
                if snapshot_url:
                    st.caption(f"[Evidence Snapshot]({BACKEND_URL}{snapshot_url})")
        else:
            st.warning("Backend offline. Start backend to view live camera stream.")

    with cam_tab2:
        st.caption("Capture a photo using your browser camera. Detection will run on the captured frame:")
        captured_img = st.camera_input("Astronaut Station Camera Input")
        if captured_img is not None:
            # Send the captured image bytes to backend for annotated detection
            try:
                img_bytes = captured_img.getvalue()
                resp = requests.post(
                    f"{BACKEND_URL}/api/v1/video/detect_image",
                    files={"file": ("webcam.jpg", img_bytes, "image/jpeg")},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    st.image(
                        resp.content,
                        caption="Detection Result — Person & Object Bounding Boxes",
                        width="stretch",
                    )
                else:
                    # Fallback: show raw image
                    st.image(img_bytes, caption="Captured Frame (Detection Unavailable)", width="stretch")
            except Exception:
                st.image(captured_img, caption="Captured Frame", width="stretch")

    with cam_tab3:
        # High-tech HUD placeholder simulating camera feed with bounding boxes
        hud_box_color = "#10b981" if status == "NORMAL" else ("#ef4444" if "VIOLATION" in status else "#eab308")
        hud_html = f"""
        <div style="
            position: relative;
            background: linear-gradient(180deg, #090d16 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 10px;
            height: 220px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 14px;
            overflow: hidden;
        ">
            <div style="display: flex; justify-content: space-between; font-family: monospace; font-size: 11px; color: #38bdf8;">
                <span>CAM-01 [OVERHEAD WORKBENCH]</span>
                <span>RESOLUTION: 1920x1080 @ 30FPS</span>
            </div>
            
            <!-- Bounding Box HUD Overlay -->
            <div style="
                margin: 0 auto;
                width: 60%;
                height: 90px;
                border: 2px dashed {hud_box_color};
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(14, 165, 233, 0.05);
            ">
                <span style="font-family: monospace; font-size: 12px; color: {hud_box_color}; font-weight: bold; background: rgba(0,0,0,0.6); padding: 2px 8px; border-radius: 4px;">
                    TARGET: {telemetry.get('current_step', {}).get('expected_action', 'OBJECT').upper()} (ZONE: {active_zone or 'A1'})
                </span>
            </div>

            <div style="display: flex; justify-content: space-between; font-family: monospace; font-size: 10px; color: #64748b;">
                <span>MEDIAPIPE HANDS: TRACKED</span>
                <span>YOLOv8 DETECTOR: ACTIVE</span>
                <span>POSE EST: CALIBRATED</span>
            </div>
        </div>
        """
        if hasattr(st, "html"):
            st.html(hud_html)
        else:
            st.markdown(hud_html, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# RIGHT COLUMN: Protocol Step Timeline Stepper & Milestones
# ----------------------------------------------------------------------------
with right_col:
    render_step_timeline(
        steps=telemetry.get("protocol_steps", []),
        progress_percentage=telemetry.get("progress_percentage", 0.0),
        current_step_id=telemetry.get("current_step", {}).get("id") if telemetry.get("current_step") else None,
    )

if hasattr(st, "html"):
    st.html("<div style='margin-bottom: 24px;'></div>")
else:
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ============================================================================
# AUDIT LOG & VERIFIABLE EVIDENCE TRAIL VIEWER
# ============================================================================

st.markdown("### 📜 Verifiable Evidence Trail & SQLite Audit Log")

col_log_actions1, col_log_actions2 = st.columns([3, 1])
with col_log_actions2:
    if backend_online:
        download_col1, download_col2 = st.columns(2)
        with download_col1:
            st.link_button("📥 JSON Logs", f"{BACKEND_URL}/api/v1/logs/export?format=json", width="stretch")
        with download_col2:
            st.link_button("📊 CSV Audit", f"{BACKEND_URL}/api/v1/logs/export?format=csv", width="stretch")

logs_response = api_get(f"/api/v1/logs/export?session_id={telemetry.get('session_id')}&format=json") if backend_online else None

if logs_response and logs_response.get("logs"):
    events_data = logs_response.get("logs", [])
    # Render table
    display_rows = []
    for ev in events_data[:15]:
        display_rows.append({
            "Timestamp": time.strftime("%H:%M:%S", time.localtime(ev.get("timestamp", time.time()))),
            "Step ID": ev.get("step_id", "N/A"),
            "Action": ev.get("action", "N/A"),
            "Zone": ev.get("rack_zone", "N/A"),
            "Validation": ev.get("validation_status", "OK"),
            "Decision": ev.get("decision_status", "VALID"),
            "Confidence": f"{float(ev.get('confidence', 1.0))*100:.0f}%",
            "Evidence ID": ev.get("evidence_id") or "N/A",
        })
    st.dataframe(display_rows, width="stretch")
else:
    # Simulated audit logs for display
    mock_logs = [
        {"Timestamp": "16:05:12", "Step ID": "S1", "Action": "identify", "Zone": "A1", "Validation": "VALID", "Decision": "VALID", "Confidence": "98%", "Evidence ID": "EV_001"},
        {"Timestamp": "16:06:44", "Step ID": "S2", "Action": "pick", "Zone": "A1", "Validation": "VALID", "Decision": "VALID", "Confidence": "95%", "Evidence ID": "EV_002"},
        {"Timestamp": "16:08:01", "Step ID": "S3", "Action": "open", "Zone": "WORKBENCH", "Validation": "VALID", "Decision": "VALID", "Confidence": "94%", "Evidence ID": "EV_003"},
    ]
    st.dataframe(mock_logs, width="stretch")

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
