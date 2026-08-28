# BAS HAR Assistant (Bio-Astronautics Human Activity Recognition Assistant)

An edge-ready, offline AI assistant designed for on-board **Bharatiya Antariksha Station (BAS)** experiment tracking and astronaut protocol verification.

---

## 📌 Features

- **Offline-Ready Architecture**: Runs fully on-board without cloud internet dependencies.
- **Protocol State Machine**: Graph-based step validation using JSON configurations with real-time sequence error detection (`SKIPPED`, `WRONG_ORDER`, `UNEXPECTED`, `COMPLETED`).
- **Camera & Processing Pipeline**: Supports live USB camera index, RTSP IP stream, or synthetic test pattern fallback.
- **Offline TTS Alerts**: Real-time non-blocking voice announcements for steps and anomaly alerts using `pyttsx3`.
- **Structured Event Logging**: Dual-mode logging to JSON Lines (`logs/events.jsonl`) and summary CSV (`logs/summary.csv`).
- **Interactive UI & REST API**: FastAPI backend exposing `/status`, `/log`, `/reset`, and `/trigger_step` endpoints with an interactive Streamlit monitoring dashboard.

---

## 📂 Project Directory Structure

```
bas_har_assistant/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── LICENSE
│
├── main.py
├── config.yaml
│
├── data/
│   ├── configs/
│   │   ├── sample_transfer_v1.json
│   │   ├── sample_experiment_v2.json
│   │   └── thresholds.json
│   │
│   ├── samples/
│   │   ├── images/
│   │   └── videos/
│   │
│   └── test_cases/
│       ├── correct_sequence.json
│       ├── wrong_sequence.json
│       ├── missing_step.json
│       └── uncertain_detection.json
│
├── models/
│   ├── object_detection/
│   │   └── README.md
│   ├── pose/
│   │   └── README.md
│   └── action/
│       └── README.md
│
├── videos/
│   ├── raw/
│   ├── processed/
│   └── evidence/
│
├── logs/
│   ├── events/
│   ├── errors/
│   └── sessions/
│
├── src/
│   │
│   ├── schemas/                   
│   │   ├── __init__.py
│   │   ├── detection.py
│   │   ├── track.py
│   │   ├── action.py
│   │   ├── protocol.py
│   │   ├── decision.py
│   │   ├── evidence.py
│   │   └── events.py
│   │
│   ├── pipeline/                 
│   │   ├── __init__.py
│   │   ├── bas_pipeline.py
│   │   ├── frame_processor.py
│   │   └── event_processor.py
│   │
│   ├── adapters/                 
│   │   ├── __init__.py
│   │   ├── detector_adapter.py
│   │   ├── pose_adapter.py
│   │   └── action_adapter.py
│   │
│   ├── interfaces/               
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── tracker.py
│   │   ├── action_recognizer.py
│   │   ├── protocol_engine.py
│   │   └── logger.py
│   │
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── capture.py
│   │   ├── opencv_camera.py
│   │   ├── synthetic_camera.py
│   │   └── camera_manager.py
│   │
│   ├── detector/
│   │   ├── __init__.py
│   │   ├── objects.py
│   │   ├── pose.py
│   │   └── inference.py
│   │
│   ├── tracker/
│   │   ├── __init__.py
│   │   ├── track.py
│   │   └── identity.py
│   │
│   ├── spatial/                   
│   │   ├── __init__.py
│   │   ├── scene.py
│   │   ├── relations.py
│   │   └── spatial_reasoner.py
│   │
│   ├── action/                     
│   │   ├── __init__.py
│   │   ├── recognizer.py
│   │   ├── temporal.py
│   │   └── action_rules.py
│   │
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── state_machine.py
│   │   ├── validator.py
│   │   └── transition.py
│   │
│   ├── decision/                  
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── confidence.py
│   │   └── recovery.py
│   │
│   ├── evidence/                
│   │   ├── __init__.py
│   │   ├── recorder.py
│   │   ├── snapshot.py
│   │   └── evidence_manager.py
│   │
│   ├── logger/
│   │   ├── __init__.py
│   │   ├── event_logger.py
│   │   ├── session_logger.py
│   │   └── structured_logger.py
│   │
│   ├── streamer/
│   │   ├── __init__.py
│   │   ├── rtsp_stub.py
│   │   └── stream_manager.py
│   │
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── offline_tts.py
│   │   └── message_generator.py
│   │
│   ├── api/                      
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── websocket.py
│   │   └── schemas.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── backend.py
│   │   ├── frontend_streamlit.py
│   │   └── components/
│   │       ├── status.py
│   │       ├── protocol.py
│   │       ├── alerts.py
│   │       └── timeline.py
│   │
│   ├── health/                    
│   │   ├── __init__.py
│   │   ├── monitor.py
│   │   └── checks.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── time.py
│       ├── ids.py
│       └── image.py
│
├── tests/
│   │
│   ├── unit/
│   │   ├── test_detector.py
│   │   ├── test_tracker.py
│   │   ├── test_protocol.py
│   │   ├── test_decision.py
│   │   └── test_recovery.py
│   │
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   ├── test_ai_protocol.py
│   │   └── test_api.py
│   │
│   ├── scenarios/
│   │   ├── test_correct_sequence.py
│   │   ├── test_wrong_sequence.py
│   │   ├── test_missing_step.py
│   │   └── test_low_confidence.py
│   │
│   └── fixtures/
│       ├── mock_detections.json
│       └── mock_actions.json
│
├── scripts/
│   ├── run_demo.py
│   ├── run_video.py
│   ├── generate_test_data.py
│   └── benchmark.py
│
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── run_local.sh
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── protocol.md
    ├── integration.md
    └── demo.md

```

---

## ⚙️ Environment Setup & Installation

1. **Clone or Navigate to the Workspace**:
   ```bash
   cd bas_har_assistant
   ```

2. **Create and Activate a Virtual Environment** (Python 3.10+ recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Running the System

### Option 1: Run Full System (FastAPI + Streamlit Dashboard)

To start both the FastAPI backend server (http://127.0.0.1:8000) and the Streamlit monitoring UI:

```bash
python main.py
```

### Option 2: Run Backend Only (Headless Edge Mode)

To run only the FastAPI backend service (e.g. for resource-constrained edge hardware):

```bash
python main.py --no-ui
```

### Option 3: Manual Execution of Backend and Streamlit Separately

1. **Terminal 1 — Start FastAPI Server**:
   ```bash
   python -c "from src.ui.backend import start_backend_server; start_backend_server()"
   ```

2. **Terminal 2 — Start Streamlit Dashboard**:
   ```bash
   streamlit run src/ui/frontend_streamlit.py
   ```

---

## 🔍 API Endpoints Summary

- **`GET /status`**: Returns current experiment step (`id`, `name`, `description`), next allowed steps, confidence level, and current alert status.
- **`GET /log`**: Retrieves recent logged step events and alerts.
- **`POST /reset`**: Resets state machine to starting step `S1`.
- **`POST /trigger_step`**: Simulates an observed activity detection event (Payload: `{"step_id": "S2", "confidence": 0.95}`).

---

## 🧩 Stubbed vs Real AI Modules Summary

| Module | Current Implementation | Real AI Upgrade Path |
| :--- | :--- | :--- |
| **Camera Capture** | OpenCV Capture / Synthetic Test Feed | High-FPS RTSP IP / USB 3.0 Industrial Cameras |
| **Detector** | Mock Bounding Boxes (`detect_objects`) & Keypoints (`estimate_pose`) | YOLOv8 / MediaPipe / RTMPose models |
| **Tracker** | Dummy Track ID Incrementor (`ObjectTracker`) | ByteTRACK / DeepSORT multi-object tracker |
| **HAR Classifier** | Rule-based & Manual Event Trigger | Spatio-Temporal Action Recognition (e.g., SlowFast / VideoMAE) |
| **State Machine** | `ProtocolStateMachine` Graph Validator | Ready for production experiment graphs |
| **TTS Engine** | `pyttsx3` Async Voice Synthesizer | Native hardware TTS / Audio Speaker system |

---

## 📝 How to Add New Experiment Protocols

To add a new experiment protocol:

1. Create a new JSON file inside `data/configs/`, e.g., `data/configs/microgravity_fluid_v1.json`.
2. Structure the JSON following this format:

```json
{
  "experiment_id": "microgravity_fluid_v1",
  "description": "Fluid dynamics mixing protocol",
  "start_step": "S1",
  "steps": [
    {
      "id": "S1",
      "name": "prepare_syringe",
      "description": "Inspect and calibrate liquid syringe",
      "allowed_next": ["S2"]
    },
    {
      "id": "S2",
      "name": "inject_fluid",
      "description": "Inject fluid sample into mixing chamber",
      "allowed_next": ["COMPLETE"]
    }
  ]
}
```

3. Launch `main.py` passing `--config data/configs/microgravity_fluid_v1.json`.
