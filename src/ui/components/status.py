"""
System Health & Spatial Rack HUD Component for BAS AI Copilot Mission Control.
Visualizes edge hardware health and the Rack-Relative Coordinate Grid (A1-C2).
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_system_health(
    system_health: Optional[Dict[str, Any]] = None,
    fps: float = 30.0,
    session_id: str = "SESSION_001",
) -> None:
    """
    Renders edge telemetry metric cards for system operational health.
    """
    health = system_health or {}
    cam_status = health.get("camera", "CONNECTED")
    inf_status = health.get("edge_inference", "OK")
    eng_status = health.get("protocol_engine", "ACTIVE")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("FPS (Edge Inference)", f"{fps:.1f}", delta=f"{cam_status}")
    with col2:
        st.metric("Protocol Engine", eng_status, delta="State Machine")
    with col3:
        st.metric("Inference Engine", inf_status, delta="YOLOv8 + ByteTrack")
    with col4:
        st.metric("Active Session", session_id[:16])


def render_rack_spatial_hud(active_zone: Optional[str] = None) -> None:
    """
    Renders the 2D Rack-Relative Coordinate Spatial Grid (A1 through C2).
    Highlights the zone currently being interacted with by the astronaut.
    """
    st.markdown("#### 🛰️ Rack-Relative Spatial Coordinate Grid")

    zones = [
        ["A1", "A2"],
        ["B1", "B2"],
        ["C1", "C2"],
    ]
    zone_labels = {
        "A1": "Sample Storage",
        "A2": "Reagent Rack",
        "B1": "Vortex / Mixer",
        "B2": "Pipette Station",
        "C1": "Waste Container",
        "C2": "Sealing Bay",
    }

    norm_active = (active_zone or "").upper()

    grid_html = """
    <div style="
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 15px;
    ">
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; margin-bottom: 8px; font-weight: 600;">
            <span>ARUCO CALIBRATED RACK FRAME</span>
            <span>COORDINATE MAPPING: NORMALIZED</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
    """

    for row in zones:
        for z in row:
            is_active = (z == norm_active)
            if is_active:
                card_bg = "linear-gradient(135deg, rgba(14, 165, 233, 0.4) 0%, rgba(2, 132, 199, 0.6) 100%)"
                border_color = "#38bdf8"
                shadow = "box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);"
                badge = "<span style='background: #0284c7; color: #ffffff; padding: 1px 6px; border-radius: 3px; font-size: 9px;'>ACTIVE INTERACTION</span>"
            else:
                card_bg = "rgba(30, 41, 59, 0.6)"
                border_color = "#334155"
                shadow = ""
                badge = ""

            grid_html += f"""
            <div style="
                background: {card_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 55px;
                {shadow}
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 14px; font-weight: bold; color: {'#38bdf8' if is_active else '#cbd5e1'}; font-family: monospace;">
                        [{z}]
                    </span>
                    {badge}
                </div>
                <div style="font-size: 11px; color: {'#e0f2fe' if is_active else '#94a3b8'};">
                    {zone_labels.get(z, 'Work Zone')}
                </div>
            </div>
            """

    grid_html += """
        </div>
    </div>
    """
    if hasattr(st, "html"):
        st.html(grid_html)
    else:
        st.markdown(grid_html, unsafe_allow_html=True)
