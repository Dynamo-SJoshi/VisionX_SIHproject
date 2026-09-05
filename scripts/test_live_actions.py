# File: scripts/test_live_actions.py
"""
Complete End-to-End Verification Script for M2 AI Perception & Action Recognition Pipeline.
Runs the master ActionRecognizer on live camera feed, detects objects, pose, tracks,
interactions, and emits real-time ActionEvent streams (PICK, OPEN, TRANSFER, SEAL, PLACE).
Saves complete video footage to logs/videos/action_recognition_output.mp4.
"""

import sys
import time
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.action import ActionRecognizer
from src.adapters import ActionAdapter


def main():
    print("==================================================")
    print("M2 AI Action Recognition Engine: Live Video & Action Stream")
    print("==================================================")

    # 1. Initialize Camera & Master Action Recognizer
    print("1. Initializing master ActionRecognizer pipeline...")
    cam = CameraCapture(source=0)
    recognizer = ActionRecognizer(frame_width=cam.width, frame_height=cam.height, action_cooldown=1.5)

    # 2. Setup Video Writer in logs/videos/
    logs_videos_dir = Path("logs") / "videos"
    logs_videos_dir.mkdir(parents=True, exist_ok=True)
    video_output_path = logs_videos_dir / "action_recognition_output.mp4"

    fps = 15.0
    total_frames = 90  # ~6 seconds of live action recognition
    frame_width = cam.width
    frame_height = cam.height

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(
        str(video_output_path),
        fourcc,
        fps,
        (frame_width, frame_height)
    )

    print(f"2. Processing and recording {total_frames} frames to {video_output_path}...")
    print("--------------------------------------------------")
    print("Instructions for testing in front of camera:")
    print("   1. Reach out your hand to touch a bottle/tube.")
    print("   2. Lift and carry the bottle across the screen (Triggers PICK).")
    print("   3. Hold it in a rack zone and release (Triggers PLACE).")
    print("--------------------------------------------------")

    all_emitted_actions = []
    start_time = time.time()
    last_action_banner = "Waiting for astronaut activity..."
    banner_color = (180, 180, 180)

    for frame_idx in range(1, total_frames + 1):
        frame, timestamp_str = cam.read_frame()
        current_timestamp = time.time() - start_time

        if frame.shape[1] != frame_width or frame.shape[0] != frame_height:
            frame = cv2.resize(frame, (frame_width, frame_height))

        # Run Master Pipeline
        confirmed_actions, telemetry = recognizer.process_frame(frame, timestamp=current_timestamp)

        # Handle newly emitted ActionEvents
        for action_event in confirmed_actions:
            all_emitted_actions.append(action_event)
            protocol_payload = ActionAdapter.to_protocol_event(action_event)
            print(f"\n[ACTION EVENT CONFIRMED at {action_event.timestamp:05.2f}s]")
            print(f"   -> Action: {action_event.action.value} | Object: {action_event.object}")
            print(f"   -> Zone: {action_event.rack_zone} | Confidence: {action_event.confidence*100:.1f}%")
            print(f"   -> Protocol Step: {protocol_payload['step_id']} | Status: {action_event.status.value}\n")

            last_action_banner = f"ACTION: {action_event.action.value} on {action_event.object} (Zone: {action_event.rack_zone})"
            banner_color = (0, 255, 0)

        # Annotate Frame with Visual Telemetry
        annotated_frame = frame.copy()

        # 1. Draw Spatial Rack Zones
        for zone in recognizer.spatial.layout.zones.values():
            z_p1 = (int(zone.bbox.x1), int(zone.bbox.y1))
            z_p2 = (int(zone.bbox.x2), int(zone.bbox.y2))
            cv2.rectangle(annotated_frame, z_p1, z_p2, (80, 80, 80), 1)
            cv2.putText(annotated_frame, zone.name, (z_p1[0] + 5, z_p1[1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

        # 2. Draw Hand & Wrist Keypoints
        for lm in telemetry.get("hand_landmarks", []):
            cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 6, (0, 0, 255), -1)

        # 3. Draw Active Tracks & Interaction Status
        for trk in telemetry.get("tracks", []):
            p1 = (int(trk.bbox.x1), int(trk.bbox.y1))
            p2 = (int(trk.bbox.x2), int(trk.bbox.y2))

            color = (0, 255, 0) if trk.class_name == "astronaut" else (255, 255, 0)
            cv2.rectangle(annotated_frame, p1, p2, color, 2)

            label = f"[ID #{trk.track_id}] {trk.class_name} ({trk.rack_zone})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated_frame, (p1[0], max(0, p1[1] - th - 6)), (p1[0] + tw + 6, p1[1]), color, -1)
            cv2.putText(annotated_frame, label, (p1[0] + 3, p1[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # 4. Draw Action Event HUD Banner at Bottom
        cv2.rectangle(annotated_frame, (0, frame_height - 40), (frame_width, frame_height), (20, 20, 20), -1)
        cv2.putText(annotated_frame, last_action_banner, (15, frame_height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, banner_color, 2)

        # 5. Top Telemetry Header
        cv2.putText(
            annotated_frame,
            f"Frame: {frame_idx:02d}/{total_frames} | M2 Action Recognizer Engine",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        video_writer.write(annotated_frame)
        time.sleep(0.04)

    video_writer.release()
    cam.release()
    recognizer.close()

    print("\n==================================================")
    print(f"Total Confirmed Action Events Emitted: {len(all_emitted_actions)}")
    print(f"Full Output Footage Saved to: {video_output_path.resolve()}")
    print("==================================================")


if __name__ == "__main__":
    main()
