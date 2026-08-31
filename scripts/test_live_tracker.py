# File: scripts/test_live_tracker.py
"""
Verification Script for Step 4: Multi-Frame Object Tracker Test
Streams frames from camera, tracks experiment object IDs over time, computes movement velocities,
prints the tracking table, and saves an annotated snapshot with motion trajectories to logs/tracker_test_output.jpg.
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
    print("Testing Step 4: Persistent Multi-Object Tracker")
    print("==================================================")

    # 1. Initialize Camera, Detector, and Tracker
    print("1. Initializing camera and tracking pipeline...")
    cam = CameraCapture(source=0)
    tracker = ObjectTracker(iou_threshold=0.15, max_center_distance=180.0, max_lost_frames=10)
    history = TrackHistoryManager(history_length=30)

    print("2. Running 20-frame live tracking sequence...")
    last_frame = None

    for frame_idx in range(1, 21):
        frame, timestamp = cam.read_frame()
        last_frame = frame.copy()

        # Detect objects (strictly whitelist-filtered)
        detections = detect_objects(frame)

        # Update tracker
        active_tracks = tracker.update(detections)
        history.record_tracks(active_tracks)

        print(f"\n--- Frame {frame_idx:02d} ({timestamp.split('T')[-1][:8]}) ---")
        if not active_tracks:
            print("  No active tracks in this frame.")
        for trk in active_tracks:
            is_moving = history.is_moving(trk.track_id, movement_threshold=12.0)
            disp = history.get_displacement(trk.track_id)
            print(
                f"  [ID #{trk.track_id}] {trk.class_name:<10} | "
                f"Velocity: ({trk.velocity[0]:>5.1f}, {trk.velocity[1]:>5.1f}) px/f | "
                f"Displacement: {disp:>5.1f}px | "
                f"Status: {'MOVING' if is_moving else 'STATIONARY'}"
            )

        time.sleep(0.05)

    # 3. Annotate the final frame with persistent IDs and trajectory trails
    if last_frame is not None:
        annotated_frame = last_frame.copy()
        tracks = list(tracker.active_tracks.values())

        for trk_state in tracks:
            # Only draw if updated recently
            if trk_state.time_since_update > 2:
                continue

            trk = trk_state.to_schema()
            p1 = (int(trk.bbox.x1), int(trk.bbox.y1))
            p2 = (int(trk.bbox.x2), int(trk.bbox.y2))

            # Color coding: Green for astronaut, Cyan for pipette/tubes, Orange for rack
            color = (0, 255, 0) if trk.class_name == "astronaut" else ((255, 255, 0) if "tube" in trk.class_name else (0, 255, 255))
            cv2.rectangle(annotated_frame, p1, p2, color, 2)

            # Draw trajectory path (Yellow trail)
            pts = history.get_trajectory(trk.track_id)
            for i in range(1, len(pts)):
                pt1 = (int(pts[i - 1][0]), int(pts[i - 1][1]))
                pt2 = (int(pts[i][0]), int(pts[i][1]))
                cv2.line(annotated_frame, pt1, pt2, (0, 255, 255), 2)

            # Draw persistent ID badge
            is_moving = history.is_moving(trk.track_id, movement_threshold=12.0)
            status_text = "MOVING" if is_moving else "STATIONARY"
            label = f"[ID #{trk.track_id}] {trk.class_name} ({status_text})"

            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            badge_y1 = max(0, p1[1] - text_h - 6)
            cv2.rectangle(annotated_frame, (p1[0], badge_y1), (p1[0] + text_w + 6, p1[1]), color, -1)
            cv2.putText(annotated_frame, label, (p1[0] + 3, p1[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        output_dir = Path("logs")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "tracker_test_output.jpg"
        cv2.imwrite(str(output_path), annotated_frame)

        print("\n==================================================")
        print(f"Visual tracking snapshot saved to: {output_path.resolve()}")
        print("==================================================")

    cam.release()


if __name__ == "__main__":
    main()
