"""
Interactive Live Experiment Script with Object and Person Detection for BAS-HAR.

Demonstrates:
1. Live camera frame capture (or synthetic test stream if camera unavailable)
2. Person detection (Astronaut detection) & Payload Object detection (tubes, pipettes, racks)
3. Centroid & IOU entity tracking with persistent track IDs
4. Semantic action recognition (Astronaut interaction)
5. Protocol State Machine validation (Step advancement & verification)
6. 3-State Safety Decision Gate (VALID, INVALID, UNCERTAIN)
7. Visual live display window with bounding boxes, labels, HUD telemetry, and safety status
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import cv2
import numpy as np

# BAS Core Architecture Imports
from src.camera.capture import CameraCapture
from src.detector.inference import YOLODetector
from src.tracker.identity import EntityTracker
from src.action.recognizer import RuleActionRecognizer
from src.protocol.engine import ProtocolEngine
from src.decision.engine import DecisionEngine
from src.logger.sqlite_logger import SQLiteLogger
from src.schemas.protocol import ProtocolStatus, ExperimentProtocol
from src.schemas.decision import DecisionStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("live_experiment")


def render_hud_overlay(
    frame: np.ndarray,
    protocol_name: str,
    current_step_name: str,
    current_step_id: str,
    decision_status: str,
    decision_message: str,
    fps: float,
    detections_count: int,
    tracks_count: int,
) -> np.ndarray:
    """Renders a futuristic on-board Mission Control HUD overlay directly on the OpenCV frame."""
    h, w = frame.shape[:2]
    canvas = frame.copy()

    # Top Mission Control Status Header Bar
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, 64), (11, 15, 25), -1)
    cv2.rectangle(overlay, (0, h - 50), (w, h), (11, 15, 25), -1)
    alpha = 0.85
    cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)

    # Top Header Text
    cv2.putText(
        canvas,
        "🛰️ BAS AI COPILOT — LIVE EXPERIMENT RUNNER",
        (16, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (56, 189, 248),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        f"FPS: {fps:4.1f} | Dets: {detections_count} | Tracks: {tracks_count}",
        (w - 260, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (148, 163, 184),
        1,
        cv2.LINE_AA,
    )

    # Protocol & Active Step info
    step_info = f"Protocol: {protocol_name}  ▶  Active Step [{current_step_id}]: {current_step_name}"
    cv2.putText(
        canvas,
        step_info,
        (16, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (226, 232, 240),
        1,
        cv2.LINE_AA,
    )

    # Decision Banner Color
    if decision_status == "VALID" or decision_status == "PROCEED":
        badge_color = (0, 220, 100)  # Green
        status_text = "🟢 [VALID] NOMINAL PROCEDURE"
    elif "UNCERTAIN" in decision_status or "VERIFY" in decision_status:
        badge_color = (0, 210, 255)  # Yellow
        status_text = "🟡 [UNCERTAIN] VERIFICATION PENDING"
    else:
        badge_color = (0, 0, 255)  # Red
        status_text = "🔴 [VIOLATION] PROCEDURE INTERRUPT"

    # Bottom Status Bar
    cv2.putText(
        canvas,
        status_text,
        (16, h - 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        badge_color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        canvas,
        decision_message[:55],
        (16, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (203, 213, 225),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        canvas,
        "Press 'q' or ESC to Exit | 's' for Snapshot | 'r' to Reset",
        (w - 380, h - 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (100, 116, 139),
        1,
        cv2.LINE_AA,
    )

    return canvas


def run_experiment(
    config_path: str = "data/configs/sample_transfer_protocol_v1.json",
    camera_source: int = 0,
    model_name: str = "yolov8n.pt",
    no_display: bool = False,
    max_frames: int = 0,
) -> None:
    """Runs end-to-end perception, tracking, action recognition, and protocol validation loop."""
    print("=" * 80)
    print("🚀 BAS HAR Assistant — Live Person & Object Detection Experiment")
    print("=" * 80)
    print(f"• Protocol Configuration: {config_path}")
    print(f"• Camera Source:          {camera_source}")
    print(f"• Object Detection Model: {model_name}")
    print("=" * 80)

    # 1. Initialize Components
    camera = CameraCapture(source=camera_source)
    detector = YOLODetector(model_name=model_name, confidence_threshold=0.30)
    tracker = EntityTracker(iou_threshold=0.25)
    recognizer = RuleActionRecognizer()
    protocol_engine = ProtocolEngine()
    decision_engine = DecisionEngine()
    logger_db = SQLiteLogger("data/logs/bas_events.db")

    # 2. Load Experiment Protocol
    cfg_file = Path(config_path)
    if cfg_file.exists():
        protocol_engine.load_protocol_from_file(cfg_file)
        logger.info(f"Loaded protocol: '{protocol_engine._protocol.name}'")
    else:
        logger.warning(f"Config file {config_path} not found. Running with baseline protocol.")

    session_id = f"EXP_LIVE_{int(time.time())}"
    logger_db.start_session(session_id, "sample_transfer_v1", time.time())

    frame_count = 0
    t_start = time.time()
    last_fps_time = time.time()
    fps = 30.0

    last_decision_status = "VALID"
    last_decision_msg = "Awaiting astronaut interaction..."

    print("\nStarting live perception pipeline loop. Press 'q' in video window to exit.")

    try:
        while True:
            t0 = time.time()
            frame_count += 1

            if max_frames > 0 and frame_count > max_frames:
                break

            # A. Acquire Video Frame
            frame, timestamp_str = camera.read_frame()

            # B. Person & Object Detection (Layer 1)
            detections = detector.detect(frame)

            # C. Multi-Object & Astronaut Tracking (Layer 2)
            tracks = tracker.update(detections)

            # D. Semantic Action Recognition (Layer 3)
            action_event = recognizer.recognize(tracks)

            # E. Protocol State Machine Validation (Layer 4)
            current_step = protocol_engine.get_current_step()
            curr_step_id = current_step.id if current_step else "DONE"
            curr_step_name = current_step.name if current_step else "Experiment Complete"
            proto_name = protocol_engine._protocol.name if protocol_engine._protocol else "Default Protocol"

            if action_event is not None and current_step is not None:
                validation = protocol_engine.validate(action_event)

                # F. 3-State Safety Decision Gate (Layer 5)
                decision = decision_engine.evaluate(validation)
                last_decision_status = (
                    decision.status.value if hasattr(decision.status, "value") else str(decision.status)
                )
                last_decision_msg = decision.message

                # Log event to SQLite Audit Log
                logger_db.log_pipeline_event(
                    session_id=session_id,
                    action=action_event,
                    validation=validation,
                    decision=decision,
                )

            # Draw Bounding Boxes and IDs on Frame
            annotated_frame = detector.draw_detections(frame, detections)

            # Draw Track IDs
            for trk in tracks:
                x1, y1, x2, y2 = trk.bbox
                tid_text = f"ID: #{trk.track_id}"
                cv2.putText(
                    annotated_frame,
                    tid_text,
                    (x1, y2 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

            # Render Full HUD Telemetry
            hud_frame = render_hud_overlay(
                frame=annotated_frame,
                protocol_name=proto_name,
                current_step_name=curr_step_name,
                current_step_id=curr_step_id,
                decision_status=last_decision_status,
                decision_message=last_decision_msg,
                fps=fps,
                detections_count=len(detections),
                tracks_count=len(tracks),
            )

            # Calculate FPS
            dt = time.time() - t0
            fps = 1.0 / dt if dt > 0 else 30.0

            # Display Window
            if not no_display:
                try:
                    cv2.imshow("BAS AI Copilot — Live Vision & Protocol Verification", hud_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in [ord("q"), 27]:  # 'q' or Esc
                        break
                    elif key == ord("r"):
                        protocol_engine.reset()
                        decision_engine.reset()
                        tracker.reset()
                        recognizer.reset()
                        logger.info("Protocol and Tracking state reset to initial step.")
                    elif key == ord("s"):
                        snap_path = f"data/evidence/snapshots/snap_{frame_count:05d}.jpg"
                        Path("data/evidence/snapshots").mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(snap_path, hud_frame)
                        logger.info(f"Saved snapshot evidence to {snap_path}")
                except Exception as e:
                    # Headless or non-GUI environment
                    if frame_count % 30 == 0:
                        logger.info(
                            f"[Headless] Frame {frame_count:04d} | Detections: {len(detections)} | Tracks: {len(tracks)} | Step: {curr_step_id} | Status: {last_decision_status}"
                        )
            else:
                if frame_count % 30 == 0:
                    logger.info(
                        f"[Headless] Frame {frame_count:04d} | Detections: {len(detections)} | Tracks: {len(tracks)} | Step: {curr_step_id} | Status: {last_decision_status}"
                    )

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        camera.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        logger_db.stop_session(session_id, time.time())
        total_time = time.time() - t_start
        print("\n" + "=" * 80)
        print(f"✅ Experiment Session '{session_id}' finished.")
        print(f"• Total Processed Frames: {frame_count}")
        print(f"• Elapsed Time:          {total_time:.2f} seconds ({frame_count / max(0.1, total_time):.1f} avg FPS)")
        print(f"• Audit Database:        data/logs/bas_events.db")
        print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Experiment with Person & Object Detection for BAS-HAR")
    parser.add_argument("--config", type=str, default="data/configs/sample_transfer_protocol_v1.json", help="Protocol JSON")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path/name (e.g. yolov8n.pt)")
    parser.add_argument("--no-display", action="store_true", help="Run in headless mode without GUI window")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 for infinite)")
    args = parser.parse_args()

    run_experiment(
        config_path=args.config,
        camera_source=args.camera,
        model_name=args.model,
        no_display=args.no_display,
        max_frames=args.max_frames,
    )
