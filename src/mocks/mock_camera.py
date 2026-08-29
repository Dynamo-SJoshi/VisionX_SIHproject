import time
from src.interfaces.camera import CameraInterface

class MockCamera(CameraInterface):
    def start(self) -> None:
        print("[CAMERA] Mock camera started")

    def read(self) -> dict:
        # Returning a fake frame dictionary instead of a real image array for now
        return {
            "frame_id": 1,
            "timestamp": time.time(),
            "data": "fake_image_bytes"
        }

    def stop(self) -> None:
        print("[CAMERA] Mock camera stopped")