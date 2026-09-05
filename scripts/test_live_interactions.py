# File: scripts/test_live_interactions.py
"""
Verification Script for Step 5: Live Spatial Zones & Hand-Object Interaction Test
Renders rack zones, calculates real-time hand-to-object distances, detects physical contact/carrying states,
and records the complete video to logs/videos/interaction_test_output.mp4.
"""

import sys
import time
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.detector import detect_objects, MediaPipePoseEstimator
from src.tracker import ObjectTracker, TrackHistoryManager
from src.spatial import SpatialReasoner
from src.action import HandObjectInteractionDetector, InteractionType


def main():
    print("==================================================")
    print("Testing Step 5: Spatial Zones & Hand-Object Interaction")
    print("==================================================")

    # 1. Initialize Pipeline Modules
    print("1. Initializing camera, detector, pose, tracker, and spatial reasoner...")
    cam = CameraCapture(source=0)
    pose_est = MediaPipePoseEstimator()
    tracker = ObjectTracker(iou_threshold=0.15, max_center_distance=200.0)
    history = TrackHistoryManager(history_length=30)
    spatial = SpatialReasoner(frame_width=cam.width, frame_height=cam.height)
    interaction_det = HandObjectInteractionDetector(contact_threshold=65.0, approach_threshold=140.0, spatial_reasoner=spatial)

    # 2. Setup Video Recording in logs/videos/
    logs_videos_dir = Path("logs") / "videos"
    logs_videos_dir.mkdir(parents=True, exist_ok=True)
    video_output_path = logs_videos_dir / "interaction_test_output.mp4"

    fps = 15.0
    total_frames = 60  # ~4 seconds of continuous interaction video
    frame_width = cam.width
    frame_height = cam.height

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(
        str(video_output_path),
        fourcc,
        fps,
        (frame_width, frame_height)
    )

    print(f"2. Recording {total_frames} frames to {video_output_path}...")
    last_annotated_frame = None

    for frame_idx in range(1, total_frames + 1):
        frame, timestamp = cam.read_frame()

        if frame.shape[1] != frame_width or frame.shape[0] != frame_height:
            frame = cv2.resize(frame, (frame_width, frame_height))

        # A. Detect Objects & Pose
        detections = detect_objects(frame)
        pose_landmarks = pose_est.estimate_pose(frame)

        # Extract wrists / hand landmarks
        hand_landmarks = [
            lm for lm in pose_landmarks
            if "wrist" in lm.name or "hand" in lm.name or "elbow" in lm.name
        ]

        # B. Track Objects
        active_tracks = tracker.update(detections)
        history.record_tracks(active_tracks)

        # C. Evaluate Hand-Object Interactions & Spatial Zones
        interactions = interaction_det.evaluate_interactions(active_tracks, hand_landmarks, history)

        # D. Annotate Frame
        annotated_frame = frame.copy()

        # 1. Draw Spatial Rack Zones (Semi-transparent grid)
        for zone in spatial.layout.zones.values():
            z_p1 = (int(zone.bbox.x1), int(zone.bbox.y1))
            z_p2 = (int(zone.bbox.x2), int(zone.bbox.y2))
            cv2.rectangle(annotated_frame, z_p1, z_p2, (100, 100, 100), 1)
            cv2.putText(
                annotated_frame,
                f"Zone [{zone.name}]",
                (z_p1[0] + 5, z_p1[1] + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (180, 180, 180),
                1
            )

        # 2. Draw Hand/Wrist Keypoints
        for lm in hand_landmarks:
            cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 6, (0, 0, 255), -1)
            cv2.putText(
                annotated_frame,
                lm.name.replace("left_", "L_").replace("right_", "R_"),
                (int(lm.x) + 8, int(lm.y) - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1
            )

        # 3. Draw Tracked Objects & Interaction Links
        for trk_state in tracker.active_tracks.values():
            if trk_state.time_since_update > 2:
                continue

            trk = trk_state.to_schema()
            p1 = (int(trk.bbox.x1), int(trk.bbox.y1))
            p2 = (int(trk.bbox.x2), int(trk.bbox.y2))

            # Match interaction record
            matched_inter = next((i for i in interactions if i.track_id == trk.track_id), None)

            if matched_inter:
                itype = matched_inter.interaction_type
                zone_str = matched_inter.rack_zone

                if itype == InteractionType.HOLD_MOVE:
                    color = (0, 255, 0)  # Bright Green (Grasping & Moving)
                    status_text = f"HOLD & CARRY [Zone: {zone_str}]"
                elif itype == InteractionType.CONTACT:
                    color = (0, 255, 255)  # Yellow (Touching / Grasping)
                    status_text = f"CONTACT [Zone: {zone_str}]"
                elif itype == InteractionType.APPROACH:
                    color = (255, 165, 0)  # Orange (Approaching)
                    status_text = f"APPROACH ({matched_inter.distance_px:.0f}px)"
                else:
                    color = (200, 200, 200)  # Gray (Idle)
                    status_text = f"IDLE [Zone: {zone_str}]"

                # Draw connection line from hand to object if nearby
                if hand_landmarks and matched_inter.distance_px < 150:
                    nearest_hand = min(hand_landmarks, key=lambda lm: ((lm.x - trk.bbox.center[0])**2 + (lm.y - trk.bbox.center[1])**2))
                    cv2.line(annotated_frame, (int(nearest_hand.x), int(nearest_hand.y)), (int(trk.bbox.center[0]), int(trk.bbox.center[1])), color, 2)
            else:
                color = (0, 255, 0) if trk.class_name == "astronaut" else (255, 255, 0)
                status_text = trk.class_name

            cv2.rectangle(annotated_frame, p1, p2, color, 2)

            # Draw badge header
            label = f"[ID #{trk.track_id}] {trk.class_name}: {status_text}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            badge_y1 = max(0, p1[1] - text_h - 6)
            cv2.rectangle(annotated_frame, (p1[0], badge_y1), (p1[0] + text_w + 6, p1[1]), color, -1)
            cv2.putText(annotated_frame, label, (p1[0] + 3, p1[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # Draw HUD Telemetry Header
        cv2.putText(
            annotated_frame,
            f"Frame: {frame_idx:02d}/{total_frames} | Spatial Rack Context & Hand-Object Interaction",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2
        )

        video_writer.write(annotated_frame)
        last_annotated_frame = annotated_frame

        if frame_idx % 15 == 0 or frame_idx == 1:
            print(f"  Frame {frame_idx:02d}/{total_frames} | Interactions active: {len(interactions)}")
            for inter in interactions:
                print(f"    -> [ID #{inter.track_id}] {inter.class_name} | State: {inter.interaction_type.value} | Dist: {inter.distance_px:.1f}px | Zone: {inter.rack_zone}")

        time.sleep(0.04)

    video_writer.release()
    cam.release()
    pose_est.close()

    # Save final snapshot
    if last_annotated_frame is not None:
        snapshot_path = Path("logs") / "interaction_test_output.jpg"
        cv2.imwrite(str(snapshot_path), last_annotated_frame)

    print("\n==================================================")
    print(f"SUCCESS: Interaction footage saved to: {video_output_path.resolve()}")
    print(f"Snapshot image saved to: {Path('logs/interaction_test_output.jpg').resolve()}")
    print("==================================================")


if __name__ == "__main__":
    main()
