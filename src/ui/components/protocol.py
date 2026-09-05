"""
Protocol & Next Recommended Action Card Component for BAS AI Copilot Mission Control.
Renders clear astronaut guidance prompts, active step requirements, and multi-modal verification tags.
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_next_action_card(
    current_step: Optional[Dict[str, Any]],
    next_step: Optional[Dict[str, Any]],
    protocol_name: str = "Active Experiment",
) -> None:
    """
    Renders a prominent Next Recommended Action Card guiding the astronaut on their immediate next interaction.
    """
    st.markdown("#### ⚡ Astronaut Guidance & Next Action")

    if not current_step:
        st.success("🎯 All protocol steps completed, or awaiting experiment start!")
        return

    curr_title = current_step.get("title", "Unknown Step")
    curr_id = current_step.get("id", "N/A")
    expected_action = current_step.get("expected_action", "Proceed with protocol")
    next_id = next_step.get("id", "Complete") if next_step else "None"
    next_title = next_step.get("title", "Completion") if next_step else "End of Procedure"

    card_html = f"""
    <div style="
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
        color: #f8fafc;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <div>
                <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; font-weight: 700;">
                    CURRENT ACTIVE STEP [{curr_id}]
                </span>
                <h2 style="margin: 2px 0 0 0; font-size: 20px; color: #38bdf8; font-weight: 700;">
                    {curr_title}
                </h2>
            </div>
            <span style="
                background: #0369a1;
                color: #e0f2fe;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                font-family: monospace;
            ">EXP: {protocol_name}</span>
        </div>

        <div style="background: rgba(15, 23, 42, 0.7); border-radius: 8px; padding: 12px; margin: 12px 0; border-left: 4px solid #38bdf8;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">
                👉 Recommended Action Directive
            </div>
            <div style="font-size: 16px; font-weight: 600; color: #ffffff;">
                {expected_action.replace('_', ' ').title()}
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #94a3b8; border-top: 1px solid #334155; padding-top: 10px;">
            <div>
                <b>Following Step:</b> <span style="color: #cbd5e1; font-weight: 600;">[{next_id}] {next_title}</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <span style="background: #1e293b; color: #10b981; border: 1px solid #10b981; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                    👁️ Visual: Enabled
                </span>
                <span style="background: #1e293b; color: #f59e0b; border: 1px solid #f59e0b; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                    ✋ Manual: Ready
                </span>
            </div>
        </div>
    </div>
    """
    if hasattr(st, "html"):
        st.html(card_html)
    else:
        st.markdown(card_html, unsafe_allow_html=True)
