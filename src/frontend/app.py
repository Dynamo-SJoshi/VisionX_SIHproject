# File: src/frontend/app.py
"""
Alias entrypoint for BAS AI Copilot Mission Control Dashboard.
Redirects to the canonical UI at src/ui/frontend_streamlit.py.
"""
from pathlib import Path
import runpy

target_script = Path(__file__).parent.parent / "ui" / "frontend_streamlit.py"
runpy.run_path(str(target_script), run_name="__main__")
