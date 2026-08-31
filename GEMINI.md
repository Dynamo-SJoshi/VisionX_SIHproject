# BAS AI Copilot — Project Overview & Architecture Guide

## 🛰️ Project Context (SIH Space Station HAR Assistant)
- **Project Name:** BAS AI Copilot / BAS HAR Assistant
- **Mission:** An offline, edge-first, safety-aware digital copilot that understands astronaut–payload interactions in a rack-relative coordinate system and verifies them against dynamically configurable scientific protocols.
- **Key Differentiator / Pitch:** Perception answers *"What happened?"* — Protocol & Decision Engine answers *"Was that valid now?"*
- **Execution Mode:** Offline-first (runs locally on edge/demo hardware; ground station telemetry stream is optional).

---

## 👥 Team Structure & Ownership

| Member | Role | Experience | Core Ownership |
|---|---|---|---|
| **M1** | System Architect + Edge AI Lead | ⭐⭐⭐ | Pipeline integration (`src/pipeline/bas_pipeline.py`), Edge optimization, Multi-threading |
| **M2** | CV / ML Lead | ⭐⭐⭐ | YOLO object detection, MediaPipe pose/hands, Tracking (ByteTrack/BoT-SORT), Temporal Action Recognition |
| **M3 (Current User)** | **Protocol + Backend Lead** | ⭐⭐⭐ | **Experiment Digital Twin, Protocol Graph / State Machine (`src/protocol/`), 3-State Decision Engine (`src/decision/`), FastAPI & WebSockets (`src/api/`), Evidence & SQLite Audit Logging (`src/evidence/`, `src/logger/`), Protocol Hot-Swapping** |
| **M4** | Dataset & Evaluation Engineer | ⭐ | Data collection (split by person: 1-3 train, 4 val, 5 test), Roboflow/YOLO annotation, Error scenarios dataset, Accuracy/Latency benchmarking |
| **M5 (Guided by M3)** | **Frontend / Mission Control Engineer** | ⭐ | **Mission Control Dashboard (Streamlit / React+Tailwind), Live video overlay, Step Progress Timeline, Status/Alert Panels, Evidence Log Viewer, CSV/JSON Exporter** |
| **M6** | Edge / QA / Hardware Integration | ⭐ | Camera positioning & mounting, ArUco rack physical calibration, Stress/Failure kill-testing (rotations, occlusions, missing steps) |

---

## 🧩 M3 Deliverables & Technical Architecture

### 1. Protocol Digital Twin (`src/protocol/`)
- Dynamic loading from `configs/experiment.json` or `data/configs/*.json`.
- State Machine / Directed Graph tracking `start_step`, prerequisites, allowed next steps, and alternate paths.
- Detects error types: `SKIPPED`, `WRONG_ORDER`, `REPEATED`, `TIMEOUT`, `UNKNOWN_STEP`, `OK`.
- Supports runtime protocol hot-swapping via API without retraining or restarting.

### 2. Decision & Safety Engine (`src/decision/`)
- **3-State Outcomes:**
  - 🟢 **`VALID`**: Step executed according to protocol -> Advance state -> Suggest next step -> Voice guidance payload.
  - 🔴 **`INVALID`**: Procedure violation -> Freeze protocol progression -> Generate human-readable violation reason.
  - 🟡 **`UNCERTAIN`**: Verification pending / "I don't know" mode -> Triggered by low confidence (< threshold) or occlusion -> Require operator confirmation.
- **Multi-Modal Verification:** Separates `visual: true` from `sensor_confirmed` or `operator_confirmed`.

### 3. Backend & Real-time Communication (`src/api/`)
- **FastAPI Framework:**
  - `GET /api/v1/protocol`: Active protocol graph structure & current step state.
  - `POST /api/v1/protocol/load`: Hot-swap experiment configuration.
  - `POST /api/v1/session/start` & `/api/v1/session/stop`: Session lifecycle control.
  - `POST /api/v1/confirm`: Manual operator/astronaut step confirmation override.
  - `GET /api/v1/logs/export`: Download session JSON/CSV audit logs.
  - `WS /ws/telemetry`: High-frequency real-time WebSocket broadcasting telemetry, bounding boxes, current step, next step, decision state, and evidence links to M5.

### 4. Evidence & Storage Engine (`src/evidence/`, `src/logger/`)
- Timestamped audit log in JSON and SQLite.
- Links decisions directly to video frame snapshots / crops for verifiable explainability.

---

## 🎨 M5 Guidance Plan (Frontend / Mission Control)

### Key UI Components:
1. **Live Camera Feed:** Video stream with bounding boxes and rack-zone overlays.
2. **Protocol Step Timeline / Stepper:** Completed steps (✓), Current active step (▶), and Upcoming steps (○).
3. **Next Recommended Action Card:** Clear instructional prompt for the astronaut/operator.
4. **Safety & Decision Banner:** Large visual status indicator (`NORMAL` 🟢, `PROCEDURE VIOLATION` 🔴, `VERIFICATION PENDING` 🟡).
5. **Real-time Event & Evidence Log:** Chronological table with timestamp, action, confidence, and snapshot thumbnail links.
6. **Session & Control Panel:** Start/Stop Session, Protocol Selector (Hot-swap), Manual Step Confirm button, CSV/JSON download buttons.

### Standard Telemetry WebSocket Schema (`/ws/telemetry`):
```json
{
  "timestamp": 1725021845.12,
  "session_id": "EXP_2026_08_30_01",
  "experiment_name": "Sample Transfer v1",
  "fps": 28.5,
  "status": "NORMAL",
  "current_step": { "id": "S4", "title": "Transfer Liquid", "state": "IN_PROGRESS" },
  "next_step": { "id": "S5", "title": "Seal Tube" },
  "progress_percentage": 60,
  "protocol_steps": [
    {"id": "S1", "title": "Identify Sample", "status": "COMPLETED"},
    {"id": "S2", "title": "Pick Tube", "status": "COMPLETED"},
    {"id": "S3", "title": "Open Tube", "status": "COMPLETED"},
    {"id": "S4", "title": "Transfer Liquid", "status": "ACTIVE"},
    {"id": "S5", "title": "Seal Tube", "status": "PENDING"},
    {"id": "S6", "title": "Place in Rack", "status": "PENDING"}
  ],
  "last_decision": {
    "type": "VALID",
    "action": "open_tube",
    "confidence": 0.94,
    "rack_zone": "A1",
    "explanation": "Tube verified open before transfer",
    "evidence_snapshot_url": "/api/v1/evidence/snap_102.jpg"
  },
  "system_health": {
    "camera": "CONNECTED",
    "edge_inference": "OK",
    "protocol_engine": "ACTIVE"
  }
}
```

---

## 🏆 Standout Differentiators for Judges
1. **Rack-Relative Coordinate Mapping** (Spatial robustness against astronaut orientation changes).
2. **Procedure-Aware Temporal State Machine** (Perception -> Verification separation).
3. **3-State Safety Gate with Uncertainty Mode** (Doesn't fail catastrophically on occlusion).
4. **Zero-Retraining Protocol Hot-Swap** (Instant adaptation to new procedures).
5. **Verifiable Evidence Chain** (Audit logs linked to visual evidence).
