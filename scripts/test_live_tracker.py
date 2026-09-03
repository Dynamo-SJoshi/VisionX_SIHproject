# File: scripts/test_live_tracker.py
"""
Verification Script for Step 4: Multi-Frame Object Tracker with Full Video Recording
Streams frames from the camera, tracks experiment object IDs over time, computes movement velocities,
draws trajectory trails, and saves the complete annotated video footage strictly to logs/videos/tracker_test_output.mp4.
"""

import sys
import time
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.detector import detect_objects
from src.tracker import ObjectTracker, TrackHistoryManager


def main():
    print("==================================================")
    print("Testing Step 4: Persistent Multi-Object Tracker (Video Recording)")
    print("==================================================")

    # 1. Initialize Camera, Detector, and Tracker
    print("1. Initializing camera and tracking pipeline...")
    cam = CameraCapture(source=0)
    tracker = ObjectTracker(iou_threshold=0.15, max_center_distance=180.0, max_lost_frames=10)
    history = TrackHistoryManager(history_length=30)

    # 2. Setup Video Writer in logs/videos/
    logs_videos_dir = Path("logs") / "videos"
    logs_videos_dir.mkdir(parents=True, exist_ok=True)
    video_output_path = logs_videos_dir / "tracker_test_output.mp4"

    fps = 15.0
    total_frames = 60  # ~4 seconds of continuous tracking video
    frame_width = cam.width
    frame_height = cam.height

    # Use mp4v codec for universal MP4 compatibility
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(
        str(video_output_path),
        fourcc,
        fps,
        (frame_width, frame_height)
    )

    print(f"2. Recording {total_frames} annotated frames directly to {video_output_path}...")
    last_annotated_frame = None

    for frame_idx in range(1, total_frames + 1):
        frame, timestamp = cam.read_frame()

        # Ensure frame dimensions match writer
        if frame.shape[1] != frame_width or frame.shape[0] != frame_height:
            frame = cv2.resize(frame, (frame_width, frame_height))

        # Detect objects (strictly whitelist-filtered)
        detections = detect_objects(frame)

        # Update tracker
        active_tracks = tracker.update(detections)
        history.record_tracks(active_tracks)

        # Annotate current frame
        annotated_frame = frame.copy()
        tracks = list(tracker.active_tracks.values())

        for trk_state in tracks:
            # Only draw if updated recently
            if trk_state.time_since_update > 2:
                continue

            trk = trk_state.to_schema()
            p1 = (int(trk.bbox.x1), int(trk.bbox.y1))
            p2 = (int(trk.bbox.x2), int(trk.bbox.y2))

            # Color coding: Green for astronaut, Cyan for pipette, Yellow for tubes, Orange for rack
            if trk.class_name == "astronaut":
                color = (0, 255, 0)
            elif trk.class_name == "pipette":
                color = (255, 255, 0)
            elif "tube" in trk.class_name:
                color = (0, 255, 255)
            else:
                color = (0, 165, 255)

            cv2.rectangle(annotated_frame, p1, p2, color, 2)

            # Draw trajectory path (Yellow trail)
            pts = history.get_trajectory(trk.track_id)
            for i in range(1, len(pts)):
                pt1 = (int(pts[i - 1][0]), int(pts[i - 1][1]))
                pt2 = (int(pts[i][0]), int(pts[i][1]))
                cv2.line(annotated_frame, pt1, pt2, (0, 255, 255), 2)

            # Draw persistent ID badge with motion status
            is_moving = history.is_moving(trk.track_id, movement_threshold=12.0)
            status_text = "MOVING" if is_moving else "STATIONARY"
            label = f"[ID #{trk.track_id}] {trk.class_name} ({status_text})"

            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            badge_y1 = max(0, p1[1] - text_h - 6)
            cv2.rectangle(annotated_frame, (p1[0], badge_y1), (p1[0] + text_w + 6, p1[1]), color, -1)
            cv2.putText(
                annotated_frame,
                label,
                (p1[0] + 3, p1[1] - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )

        # Draw frame counter & HUD timestamp
        cv2.putText(
            annotated_frame,
            f"Frame: {frame_idx:02d}/{total_frames} | BAS HAR Multi-Object Tracker",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2
        )

        # Write frame to output video file
        video_writer.write(annotated_frame)
        last_annotated_frame = annotated_frame

        if frame_idx % 10 == 0 or frame_idx == 1:
            print(f"  Recorded frame {frame_idx:02d}/{total_frames} | Active Tracks: {len(active_tracks)}")
            for trk in active_tracks:
                is_mov = history.is_moving(trk.track_id, movement_threshold=12.0)
                print(f"    -> [ID #{trk.track_id}] {trk.class_name:<10} (Status: {'MOVING' if is_mov else 'STATIONARY'})")

        time.sleep(0.04)

    # 3. Clean up and finalize files
    video_writer.release()
    cam.release()

    # Save latest snapshot in logs/
    if last_annotated_frame is not None:
        snapshot_path = Path("logs") / "tracker_test_output.jpg"
        cv2.imwrite(str(snapshot_path), last_annotated_frame)

    print("\n==================================================")
    print(f"SUCCESS: Video footage stored at: {video_output_path.resolve()}")
    print(f"Snapshot image stored at: {Path('logs/tracker_test_output.jpg').resolve()}")
    print("==================================================")


if __name__ == "__main__":
    main()
