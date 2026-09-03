# File: main.py
"""
BAS HAR Assistant — Main Entry Point

Launches the offline FastAPI backend and Streamlit dashboard for on-board activity recognition and protocol monitoring.
"""

import argparse
import logging
import os
import sys
import subprocess
import threading
import time
from pathlib import Path

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def start_fastapi_server(host: str, port: int):
    """Runs the FastAPI backend using Uvicorn."""
    from src.api.routes import app
    logger.info(f"Starting FastAPI backend server on http://{host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")


def launch_streamlit_frontend():
    """Launches the Streamlit frontend UI as a subprocess."""
    script_path = Path(__file__).parent / "src" / "frontend" / "app.py"
    if not script_path.exists():
        script_path = Path(__file__).parent / "frontend" / "app.py"

    if script_path.exists():
        logger.info(f"Launching Streamlit dashboard frontend from {script_path}...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(script_path)])
    else:
        logger.warning("Streamlit frontend script not found. Running in backend-only mode.")


def main():
    parser = argparse.ArgumentParser(description="BAS HAR Assistant — On-board Experiment AI Assistant")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Backend API host address")
    parser.add_argument("--port", type=int, default=8000, help="Backend API port number")
    parser.add_argument("--config", type=str, default="data/configs/sample_transfer_protocol_v1.json", help="Path to experiment protocol JSON")
    parser.add_argument("--no-ui", action="store_true", help="Run backend API only without Streamlit dashboard")
    args = parser.parse_args()

    # Ensure log & data folders exist
    Path("logs").mkdir(exist_ok=True)
    Path("logs/videos").mkdir(parents=True, exist_ok=True)
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    Path("data/evidence/snapshots").mkdir(parents=True, exist_ok=True)

    logger.info("==================================================")
    logger.info("🚀 BAS HAR Assistant — Offline On-board AI Assistant")
    logger.info("==================================================")
    logger.info(f"Protocol Config: {args.config}")

    if args.no_ui:
        start_fastapi_server(args.host, args.port)
    else:
        # Start FastAPI backend in a daemon background thread
        backend_thread = threading.Thread(
            target=start_fastapi_server,
            args=(args.host, args.port),
            daemon=True
        )
        backend_thread.start()

        # Wait for FastAPI to initialize
        time.sleep(2)

        # Launch Streamlit dashboard in main process
        try:
            launch_streamlit_frontend()
        except KeyboardInterrupt:
            logger.info("Shutting down BAS HAR Assistant.")


if __name__ == "__main__":
    main()