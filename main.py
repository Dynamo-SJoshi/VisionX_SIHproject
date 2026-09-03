"""
BAS-HAR Assistant — Main Entry Point

Responsibilities of this file:

    1. Validate basic application configuration.
    2. Prepare required directories.
    3. Launch the FastAPI backend.
    4. Optionally launch the Streamlit dashboard.

Important architectural rule:

    main.py
        ↓
    FastAPI backend
        ↓
    BASPipeline
        ↓
    Camera → AI → Protocol → Decision → Logger

The actual BAS-HAR processing logic must NOT live here.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "[%(levelname)s] "
        "%(name)s - "
        "%(message)s"
    ),
)

logger = logging.getLogger("bas_har.main")


# ============================================================================
# PROJECT PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = DATA_DIR / "configs"

LOGS_DIR = PROJECT_ROOT / "logs"
VIDEOS_DIR = PROJECT_ROOT / "videos"

STREAMLIT_SCRIPT = (
    PROJECT_ROOT
    / "src"
    / "ui"
    / "frontend_streamlit.py"
)


# ============================================================================
# DIRECTORY PREPARATION
# ============================================================================

def prepare_directories() -> None:
    """
    Create directories required by the application.

    Existing directories are left untouched.
    """

    directories = [
        DATA_DIR,
        CONFIG_DIR,
        LOGS_DIR,
        VIDEOS_DIR,
    ]

    for directory in directories:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.debug(
            "Directory ready: %s",
            directory,
        )


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config(
    config_path: str,
) -> Path:
    """
    Validate that the selected protocol configuration exists.

    Note:
        main.py does not parse the protocol itself.
        The protocol engine is responsible for interpreting it.

    Args:
        config_path:
            Path to the experiment protocol JSON.

    Returns:
        Resolved configuration path.

    Raises:
        FileNotFoundError:
            If the protocol file does not exist.
    """

    path = Path(config_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    path = path.resolve()

    if not path.exists():

        raise FileNotFoundError(
            f"Protocol configuration not found: {path}"
        )

    if not path.is_file():

        raise FileNotFoundError(
            f"Protocol configuration is not a file: {path}"
        )

    logger.info(
        "Protocol configuration: %s",
        path,
    )

    return path


# ============================================================================
# FASTAPI SERVER
# ============================================================================

def start_fastapi_server(
    host: str,
    port: int,
) -> None:
    """
    Start the existing BAS-HAR FastAPI application.

    backend.py owns the FastAPI application object.
    main.py only launches it.
    """

    from src.ui.backend import app

    logger.info(
        "Starting FastAPI backend on http://%s:%d",
        host,
        port,
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


# ============================================================================
# STREAMLIT FRONTEND
# ============================================================================

def launch_streamlit_frontend(
    backend_host: str,
    backend_port: int,
) -> int:
    """
    Launch the Streamlit dashboard.

    Environment variables are passed so the frontend knows where
    the FastAPI backend is running.

    Returns:
        Streamlit subprocess exit code.
    """

    if not STREAMLIT_SCRIPT.exists():

        raise FileNotFoundError(
            "Streamlit frontend not found at: "
            f"{STREAMLIT_SCRIPT}"
        )

    logger.info(
        "Launching Streamlit dashboard..."
    )

    logger.info(
        "Frontend backend target: http://%s:%d",
        backend_host,
        backend_port,
    )

    # The frontend can later read these values using os.getenv().
    import os

    environment = os.environ.copy()

    environment[
        "BAS_HAR_API_HOST"
    ] = backend_host

    environment[
        "BAS_HAR_API_PORT"
    ] = str(backend_port)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(STREAMLIT_SCRIPT),
        ],
        cwd=str(PROJECT_ROOT),
        env=environment,
    )

    return process.wait()


# ============================================================================
# STARTUP WAIT
# ============================================================================

def wait_for_backend(
    host: str,
    port: int,
    timeout: float = 10.0,
) -> bool:
    """
    Wait until the FastAPI backend accepts a TCP connection.

    This is more reliable than a fixed two-second sleep.

    Returns:
        True if the backend becomes reachable.
        False if the timeout expires.
    """

    import socket

    start_time = time.monotonic()

    while (
        time.monotonic() - start_time
        < timeout
    ):

        try:

            with socket.create_connection(
                (host, port),
                timeout=0.5,
            ):
                logger.info(
                    "FastAPI backend is reachable."
                )

                return True

        except OSError:

            time.sleep(0.25)

    logger.error(
        "FastAPI backend did not become reachable "
        "within %.1f seconds.",
        timeout,
    )

    return False


# ============================================================================
# APPLICATION SHUTDOWN
# ============================================================================

def shutdown_message() -> None:
    """
    Log a clean shutdown message.
    """

    logger.info(
        "Shutting down BAS-HAR Assistant."
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """
    Main application entry point.
    """

    parser = argparse.ArgumentParser(
        description=(
            "BAS-HAR Assistant — "
            "On-board Activity Recognition "
            "and Experiment Procedure Monitoring"
        )
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help=(
            "FastAPI host address. "
            "Default: 127.0.0.1"
        ),
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help=(
            "FastAPI port. "
            "Default: 8000"
        ),
    )

    parser.add_argument(
        "--config",
        type=str,
        default="data/configs/sample_transfer_v1.json",
        help=(
            "Path to experiment protocol JSON."
        ),
    )

    parser.add_argument(
        "--no-ui",
        action="store_true",
        help=(
            "Start only the FastAPI backend "
            "without the Streamlit dashboard."
        ),
    )

    parser.add_argument(
        "--no-backend",
        action="store_true",
        help=(
            "Start only the Streamlit frontend. "
            "Use only when a backend is already running."
        ),
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------------
    # STARTUP BANNER
    # ------------------------------------------------------------------------

    logger.info("=" * 64)
    logger.info(
        "BAS-HAR Assistant — Offline On-Board AI System"
    )
    logger.info("=" * 64)

    # ------------------------------------------------------------------------
    # PREPARE FILESYSTEM
    # ------------------------------------------------------------------------

    prepare_directories()

    # ------------------------------------------------------------------------
    # VALIDATE PROTOCOL CONFIG
    # ------------------------------------------------------------------------

    try:

        config_path = validate_config(
            args.config
        )

    except FileNotFoundError as exc:

        logger.error(
            "%s",
            exc,
        )

        return 1

    logger.info(
        "Protocol ready: %s",
        config_path.name,
    )

    # ------------------------------------------------------------------------
    # BACKEND-ONLY MODE
    # ------------------------------------------------------------------------

    if args.no_ui:

        try:

            start_fastapi_server(
                args.host,
                args.port,
            )

        except KeyboardInterrupt:

            shutdown_message()

        return 0

    # ------------------------------------------------------------------------
    # FRONTEND-ONLY MODE
    # ------------------------------------------------------------------------

    if args.no_backend:

        try:

            exit_code = launch_streamlit_frontend(
                args.host,
                args.port,
            )

            return exit_code

        except KeyboardInterrupt:

            shutdown_message()

            return 0

    # ------------------------------------------------------------------------
    # NORMAL MODE
    #
    # Start FastAPI in a background thread and launch Streamlit.
    # ------------------------------------------------------------------------

    backend_thread = threading.Thread(
        target=start_fastapi_server,
        args=(
            args.host,
            args.port,
        ),
        name="bas-har-fastapi",
        daemon=True,
    )

    logger.info(
        "Starting BAS-HAR backend thread..."
    )

    backend_thread.start()

    # Wait for backend instead of assuming that two seconds is enough.
    backend_ready = wait_for_backend(
        args.host,
        args.port,
        timeout=10.0,
    )

    if not backend_ready:

        logger.error(
            "Backend failed to start. "
            "Streamlit will not be launched."
        )

        return 1

    # ------------------------------------------------------------------------
    # LAUNCH STREAMLIT
    # ------------------------------------------------------------------------

    try:

        exit_code = launch_streamlit_frontend(
            args.host,
            args.port,
        )

        return exit_code

    except KeyboardInterrupt:

        shutdown_message()

        return 0

    except FileNotFoundError as exc:

        logger.error(
            "%s",
            exc,
        )

        return 1

    finally:

        shutdown_message()


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())