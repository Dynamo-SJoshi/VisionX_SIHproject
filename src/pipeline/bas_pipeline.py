from src.interfaces.camera import CameraInterface
from src.interfaces.detector import DetectorInterface
from src.interfaces.tracker import TrackerInterface
from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.interfaces.protocol_engine import ProtocolEngineInterface
from src.interfaces.decision_engine import DecisionEngineInterface
from src.interfaces.logger import LoggerInterface
from src.schemas.decision import Decision

class BASPipeline:
    def __init__(
        self,
        camera: CameraInterface,
        detector: DetectorInterface,
        tracker: TrackerInterface,
        action_recognizer: ActionRecognizerInterface,
        protocol_engine: ProtocolEngineInterface,
        decision_engine: DecisionEngineInterface,
        logger: LoggerInterface
    ):
        self.camera = camera
        self.detector = detector
        self.tracker = tracker
        self.action_recognizer = action_recognizer
        self.protocol_engine = protocol_engine
        self.decision_engine = decision_engine
        self.logger = logger

    def process_frame(self, frame: any) -> Decision:
        print("\n========== FRAME PROCESSING ==========")
        
        # 1. Perception Layer (M2's domain)
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections)
        action = self.action_recognizer.recognize(tracks)
        
        print(f"[PIPELINE] Action Recognized: {action.action.value}")

        # 2. Reasoning Layer (M3's domain)
        validation = self.protocol_engine.validate(action)
        print(f"[PIPELINE] Protocol Status: {validation.status.value}")

        # 3. Decision Layer (Your domain)
        decision = self.decision_engine.evaluate(validation)
        print(f"[PIPELINE] Decision: {decision.status.value} -> {decision.message}")

        # 4. Infrastructure Layer
        self.logger.log_event(action, validation, decision)

        return decision