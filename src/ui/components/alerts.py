"""
Alerts & Decision Banner Component for BAS AI Copilot Mission Control.
Provides a 3-state visual status indicator:
  - 🟢 NORMAL (VALID): Protocol execution is on track.
  - 🔴 PROCEDURE VIOLATION (INVALID): Rule or sequence breach detected.
  - 🟡 VERIFICATION PENDING (UNCERTAIN): Occlusion, low confidence, or operator confirmation needed.
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_decision_banner(status: str, last_decision: Optional[Dict[str, Any]] = None) -> None:
    """
    Renders the prominent 3-state Safety & Decision Banner at the top of Mission Control.
    """
    normalized_status = (status or "NORMAL").upper()

    # Style definitions for 3 states
    if "VIOLATION" in normalized_status or (last_decision and last_decision.get("type") == "INVALID"):
        theme = {
            "bg": "linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(127, 29, 29, 0.45) 100%)",
            "border": "#ef4444",
            "text_color": "#fca5a5",
            "badge_bg": "#b91c1c",
            "badge_text": "#fee2e2",
            "icon": "🚨",
            "title": "PROCEDURE VIOLATION DETECTED",
            "default_msg": "Protocol progression halted. Astronaut safety check or sequence correction required.",
        }
    elif "PENDING" in normalized_status or (last_decision and last_decision.get("type") == "UNCERTAIN"):
        theme = {
            "bg": "linear-gradient(135deg, rgba(234, 179, 8, 0.25) 0%, rgba(113, 63, 18, 0.45) 100%)",
            "border": "#eab308",
            "text_color": "#fde047",
            "badge_bg": "#854d0e",
            "badge_text": "#fef9c3",
            "icon": "⚠️",
            "title": "VERIFICATION PENDING / UNCERTAINTY MODE",
            "default_msg": "Low confidence observation or partial occlusion. Manual operator confirmation recommended.",
        }
    else:
        theme = {
            "bg": "linear-gradient(135deg, rgba(16, 185, 129, 0.20) 0%, rgba(6, 78, 59, 0.40) 100%)",
            "border": "#10b981",
            "text_color": "#6ee7b7",
            "badge_bg": "#065f46",
            "badge_text": "#d1fae5",
            "icon": "🟢",
            "title": "PROTOCOL NORMAL — NOMINAL EXECUTION",
            "default_msg": "All actions validated against active flight experiment protocol.",
        }

    explanation = (
        last_decision.get("explanation")
        if last_decision and last_decision.get("explanation")
        else theme["default_msg"]
    )
    confidence = last_decision.get("confidence") if last_decision else None
    action = last_decision.get("action") if last_decision else None
    rack_zone = last_decision.get("rack_zone") if last_decision else None
    voice_msg = last_decision.get("voice_message") if last_decision else None

    # HTML Banner
    banner_html = f"""
    <div style="
        background: {theme['bg']};
        border: 2px solid {theme['border']};
        border-radius: 12px;
        padding: 16px 22px;
        margin-bottom: 20px;
        box-shadow: 0 0 20px {theme['border']}33;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 28px;">{theme['icon']}</span>
                <div>
                    <span style="
                        background-color: {theme['badge_bg']};
                        color: {theme['badge_text']};
                        font-size: 11px;
                        font-weight: 700;
                        letter-spacing: 1.5px;
                        padding: 3px 10px;
                        border-radius: 9999px;
                        text-transform: uppercase;
                        border: 1px solid {theme['border']};
                    ">{normalized_status}</span>
                    <h3 style="margin: 4px 0 0 0; font-size: 18px; font-weight: 700; color: {theme['text_color']};">
                        {theme['title']}
                    </h3>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                {f'<span style="background: rgba(15, 23, 42, 0.7); padding: 5px 12px; border-radius: 6px; border: 1px solid #334155; font-size: 12px; font-family: monospace;"><b>Zone:</b> {rack_zone}</span>' if rack_zone else ''}
                {f'<span style="background: rgba(15, 23, 42, 0.7); padding: 5px 12px; border-radius: 6px; border: 1px solid #334155; font-size: 12px; font-family: monospace;"><b>Action:</b> {action}</span>' if action else ''}
                {f'<span style="background: rgba(15, 23, 42, 0.7); padding: 5px 12px; border-radius: 6px; border: 1px solid #334155; font-size: 12px; font-family: monospace;"><b>Conf:</b> {int(confidence*100)}%</span>' if confidence is not None else ''}
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 14px; color: #e2e8f0; line-height: 1.5; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 8px;">
            <b>Explanation:</b> {explanation}
        </div>
        {f'''
        <div style="margin-top: 6px; font-size: 13px; color: #94a3b8; font-style: italic;">
            🔊 <b>Audio Dispatch:</b> "{voice_msg}"
        </div>
        ''' if voice_msg else ''}
    </div>
    """
    if hasattr(st, "html"):
        st.html(banner_html)
    else:
        st.markdown(banner_html, unsafe_allow_html=True)
