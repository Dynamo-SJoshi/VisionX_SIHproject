# File: scripts/test_live_detector.py
"""
Verification Script for Step 2 & 3: Camera + YOLO Object Detector + Real Neural Pose Estimator
Captures a video frame, runs YOLOObjectDetector, MediaPipePoseEstimator, MediaPipeHandEstimator,
prints results, and saves a crisp annotated test image to logs/detector_test_output.jpg.
"""

import sys
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.detector import detect_objects, MediaPipePoseEstimator, MediaPipeHandEstimator

# Skeleton connections between keypoint indices for pose drawing
SKELETON_PAIRS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip")
]


def main():
    print("==================================================")
    print("Testing Step 2 & 3: YOLO Detector + Real Pose Estimator")
    print("==================================================")

    # 1. Initialize Camera & Estimators
    print("1. Initializing camera feed and AI neural estimators...")
    cam = CameraCapture(source=0)
    pose_est = MediaPipePoseEstimator()
    hand_est = MediaPipeHandEstimator()

    # 2. Read Frame
    frame, timestamp = cam.read_frame()
    print(f"2. Frame captured successfully at timestamp: {timestamp}")
    print(f"   Frame shape: {frame.shape[1]}x{frame.shape[0]} pixels")

    # 3. Run YOLO Object Detector
    print("3. Running YOLO Object Detector (Conf Threshold >= 0.45)...")
    detections = detect_objects(frame)
    print(f"   Found {len(detections)} object detections:")
    for d in detections:
        print(f"   - {d.class_name:<12} (Confidence: {d.confidence*100:.1f}%) at [{d.bbox.x1:.0f}, {d.bbox.y1:.0f}, {d.bbox.x2:.0f}, {d.bbox.y2:.0f}]")

    # 4. Run Pose Estimator
    print("4. Running Pose Estimator...")
    pose_landmarks = pose_est.estimate_pose(frame)
    print(f"   Pose Landmarks detected: {len(pose_landmarks)} keypoints")
    for lm in pose_landmarks:
        print(f"   - Joint: {lm.name:<16} at ({lm.x:.1f}, {lm.y:.1f})")

    # 5. Annotate Image with clean visuals
    annotated_frame = frame.copy()

    # Draw Skeletal Bones
    lm_dict = {lm.name: (int(lm.x), int(lm.y)) for lm in pose_landmarks}
    for pt1_name, pt2_name in SKELETON_PAIRS:
        if pt1_name in lm_dict and pt2_name in lm_dict:
            cv2.line(annotated_frame, lm_dict[pt1_name], lm_dict[pt2_name], (255, 105, 180), 2)

    # Draw Pose Joint Keypoints
    for lm in pose_landmarks:
        cv2.circle(annotated_frame, (int(lm.x), int(lm.y)), 5, (0, 255, 255), -1)

    # Draw YOLO Bounding Boxes with solid background text badges
    for d in detections:
        p1 = (int(d.bbox.x1), int(d.bbox.y1))
        p2 = (int(d.bbox.x2), int(d.bbox.y2))
        cv2.rectangle(annotated_frame, p1, p2, (0, 255, 0), 2)

        label_text = f"{d.class_name} {d.confidence*100:.0f}%"
        (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        badge_y1 = max(0, p1[1] - text_h - 6)
        cv2.rectangle(annotated_frame, (p1[0], badge_y1), (p1[0] + text_w + 6, p1[1]), (0, 255, 0), -1)
        cv2.putText(
            annotated_frame,
            label_text,
            (p1[0] + 3, p1[1] - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA
        )

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
