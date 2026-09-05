"""
Protocol Step Timeline / Stepper Component for BAS AI Copilot Mission Control.
Visualizes completed (✓), active (▶), and upcoming (○) experiment steps,
along with overall procedure completion percentage.
"""

from typing import Any, Dict, List, Optional
import streamlit as st


def render_step_timeline(
    steps: List[Dict[str, Any]],
    progress_percentage: float = 0.0,
    current_step_id: Optional[str] = None,
) -> None:
    """
    Renders an on-board timeline stepper displaying all protocol milestones and current progression.
    """
    st.markdown("#### 🧭 Protocol Execution Stepper")

    # Overall progress bar
    progress_int = max(0, min(100, int(progress_percentage)))
    progress_html = f"""
    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8; margin-bottom: 6px;">
        <span>Overall Progress</span>
        <span style="color: #38bdf8; font-weight: 700;">{progress_percentage:.1f}% Complete</span>
    </div>
    """
    if hasattr(st, "html"):
        st.html(progress_html)
    else:
        st.markdown(progress_html, unsafe_allow_html=True)
    st.progress(progress_int / 100.0)

    if not steps:
        st.info("No active protocol loaded.")
        return

    # Visual Stepper Cards
    step_cards_html = """<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 14px;">"""

    for idx, step in enumerate(steps, start=1):
        step_id = step.get("id", f"S{idx}")
        title = step.get("title", f"Step {idx}")
        raw_status = step.get("status", "PENDING").upper()
        allowed_next = step.get("allowed_next", [])
        is_active = (raw_status == "ACTIVE") or (current_step_id and step_id == current_step_id)

        if raw_status == "COMPLETED":
            bg = "rgba(16, 185, 129, 0.12)"
            border = "#10b981"
            icon = "✓"
            badge_bg = "#065f46"
            badge_color = "#34d399"
            badge_text = "COMPLETED"
            text_color = "#e2e8f0"
        elif is_active:
            bg = "linear-gradient(90deg, rgba(14, 165, 233, 0.25) 0%, rgba(3, 105, 161, 0.35) 100%)"
            border = "#38bdf8"
            icon = "▶"
            badge_bg = "#0369a1"
            badge_color = "#7dd3fc"
            badge_text = "IN PROGRESS"
            text_color = "#38bdf8"
        else:
            bg = "rgba(30, 41, 59, 0.45)"
            border = "#334155"
            icon = "○"
            badge_bg = "#1e293b"
            badge_color = "#94a3b8"
            badge_text = "PENDING"
            text_color = "#94a3b8"

        next_info = f"<span style='font-size: 11px; color: #64748b; margin-left: 8px;'>Next: {', '.join(allowed_next)}</span>" if allowed_next else ""

        step_cards_html += f"""
        <div style="
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
            {'box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);' if is_active else ''}
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 26px;
                    height: 26px;
                    border-radius: 50%;
                    background: {badge_bg};
                    color: {badge_color};
                    font-weight: bold;
                    font-size: 13px;
                ">{icon}</span>
                <div>
                    <span style="font-family: monospace; font-size: 11px; color: #38bdf8; font-weight: bold; margin-right: 6px;">[{step_id}]</span>
                    <span style="font-weight: 600; font-size: 14px; color: {text_color};">{title}</span>
                    {next_info}
                </div>
            </div>
            <span style="
                background: {badge_bg};
                color: {badge_color};
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
                border-radius: 4px;
                letter-spacing: 0.8px;
            ">{badge_text}</span>
        </div>
        """

    step_cards_html += "</div>"
    if hasattr(st, "html"):
        st.html(step_cards_html)
    else:
        st.markdown(step_cards_html, unsafe_allow_html=True)
