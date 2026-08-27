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
├── data/
│   └── configs/
│       └── sample_transfer_v1.json   # Experiment protocol graph definition
├── logs/                             # Output JSONL and CSV logs
├── videos/                           # Recorded video clips & timestamps
├── src/
│   ├── camera/
│   │   ├── __init__.py
│   │   └── capture.py                # OpenCV / RTSP / Synthetic camera feed handler
│   ├── detector/
│   │   ├── __init__.py
│   │   ├── objects.py                # Object detection stubs
│   │   └── pose.py                   # Pose / skeleton estimation stubs
│   ├── tracker/
│   │   ├── __init__.py
│   │   └── track.py                  # Object / person track ID tracker stub
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── graph.py                  # Protocol graph JSON loader
│   │   └── state_machine.py          # State transition & validation engine
│   ├── logger/
│   │   ├── __init__.py
│   │   └── event_logger.py           # Thread-safe JSONL/CSV event logger
│   ├── streamer/
│   │   ├── __init__.py
│   │   └── rtsp_stub.py              # RTSP IP video streaming stub
│   ├── tts/
│   │   ├── __init__.py
│   │   └── offline_tts.py            # Async pyttsx3 voice synthesizer
│   └── ui/
│       ├── __init__.py
│       ├── backend.py                # FastAPI REST API & background loop
│       └── frontend_streamlit.py     # Streamlit real-time monitoring dashboard
├── main.py                           # System entry point
├── requirements.txt                  # Python dependencies
└── README.md                         # Documentation
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
