# File: scripts/test_live_detector.py
"""
Verification Script for Step 2 & 3: Camera + YOLO Detector + MediaPipe Pose & Hands
Captures a video frame, runs YOLOObjectDetector, MediaPipePoseEstimator, MediaPipeHandEstimator,
prints results, and saves an annotated test image to logs/detector_test_output.jpg.
"""

import sys
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.detector import detect_objects, MediaPipePoseEstimator, MediaPipeHandEstimator


def main():
    print("==================================================")
    print("Testing Step 2 & 3: YOLO + MediaPipe Pose & Hands")
    print("==================================================")

    # 1. Initialize Camera & Estimators
    print("1. Initializing camera feed and AI estimators...")
    cam = CameraCapture(source=0)
    pose_est = MediaPipePoseEstimator()
    hand_est = MediaPipeHandEstimator()

    # 2. Read Frame
    frame, timestamp = cam.read_frame()
    print(f"2. Frame captured successfully at timestamp: {timestamp}")
    print(f"   Frame shape: {frame.shape[1]}x{frame.shape[0]} pixels")

    # 3. Run YOLO Object Detector
    print("3. Running YOLO Object Detector...")
    detections = detect_objects(frame)
    print(f"   Found {len(detections)} object detections.")

    # 4. Run MediaPipe Pose & Hands Estimator
    print("4. Running MediaPipe Pose & Hands Estimators...")
    pose_landmarks = pose_est.estimate_pose(frame)
    left_hand, right_hand = hand_est.estimate_hands(frame)
    print(f"   Pose Landmarks: {len(pose_landmarks)} keypoints")
    print(f"   Left Hand Keypoints: {len(left_hand)}, Right Hand Keypoints: {len(right_hand)}")

    # Annotate frame
    annotated_frame = frame.copy()

    # Draw YOLO Bounding Boxes
    for d in detections:
        p1 = (int(d.bbox.x1), int(d.bbox.y1))
        p2 = (int(d.bbox.x2), int(d.bbox.y2))
        cv2.rectangle(annotated_frame, p1, p2, (0, 255, 0), 2)
        cv2.putText(
            annotated_frame,
            f"{d.class_name} ({d.confidence*100:.0f}%)",
            (p1[0], max(p1[1] - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    # Draw Pose Keypoints (Blue dots)
    for lm in pose_landmarks:
        cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 4, (255, 0, 0), -1)

    # Draw Hand Keypoints (Red/Yellow dots)
    for lm in left_hand:
        cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 3, (0, 0, 255), -1)
    for lm in right_hand:
        cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 3, (0, 255, 255), -1)

    # Save output image
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "detector_test_output.jpg"
    cv2.imwrite(str(output_path), annotated_frame)

    print("--------------------------------------------------")
    print(f"Visual output image saved to: {output_path.resolve()}")
    print("==================================================")

    # Cleanup
    cam.release()
    pose_est.close()
    hand_est.close()


if __name__ == "__main__":
    main()
