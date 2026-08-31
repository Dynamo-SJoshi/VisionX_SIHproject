# File: scripts/test_live_detector.py
"""
Verification Script for Step 2: Live Camera & Object Detector Test
Captures a video frame, runs YOLOObjectDetector, prints detections, and saves an annotated test image to logs/.
"""

import sys
from pathlib import Path
import cv2

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import CameraCapture
from src.detector import detect_objects


def main():
    print("==================================================")
    print("Testing Step 2: Camera Capture + Object Detector")
    print("==================================================")

    # 1. Initialize Camera Capture
    print("1. Initializing camera feed...")
    cam = CameraCapture(source=0)

    # 2. Read Frame
    frame, timestamp = cam.read_frame()
    print(f"2. Frame captured successfully at timestamp: {timestamp}")
    print(f"   Frame shape: {frame.shape[1]}x{frame.shape[0]} pixels")

    # 3. Run YOLO Object Detector
    print("3. Running YOLO Object Detector...")
    detections = detect_objects(frame)

    print(f"\nFound {len(detections)} object detections:")
    print("--------------------------------------------------")
    print(f"{'CLASS NAME':<15} | {'CONFIDENCE':<10} | {'BOUNDING BOX [X1, Y1, X2, Y2]'}")
    print("--------------------------------------------------")

    # Annotate frame with bounding boxes
    annotated_frame = frame.copy()
    for d in detections:
        bbox_str = f"[{d.bbox.x1:.0f}, {d.bbox.y1:.0f}, {d.bbox.x2:.0f}, {d.bbox.y2:.0f}]"
        print(f"{d.class_name:<15} | {d.confidence*100:>8.1f}% | {bbox_str}")

        # Draw box & text on output image
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

    # 4. Save annotated image for visual verification
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "detector_test_output.jpg"
    cv2.imwrite(str(output_path), annotated_frame)

    print("--------------------------------------------------")
    print(f"Visual output image saved to: {output_path.resolve()}")
    print("==================================================")

    # Release camera
    cam.release()


if __name__ == "__main__":
    main()
