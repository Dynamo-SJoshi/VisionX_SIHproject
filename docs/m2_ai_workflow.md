# M2 — AI/Computer Vision Workflow Context

Use the following as the **fixed context for M2's future AI/ML work**. The goal is to keep M2 focused on the perception/action-recognition part without changing the overall system architecture.

---

### Project context

We are building an **offline-first AI Human Activity Recognition + Experiment Procedure Validation system for onboard BAS experiments**.

The system watches a fixed camera feed of an astronaut performing **one predefined experiment** and converts raw video into structured actions that the protocol engine can validate.

**M2 owns the AI perception and action-recognition pipeline.**

M2 does **not** own the protocol logic, dashboard, TTS, or backend architecture.

---

# M2's pipeline

```text
CAMERA FRAME
     ↓
OBJECT DETECTION
     ↓
POSE + HAND DETECTION
     ↓
OBJECT/PERSON TRACKING
     ↓
SPATIAL / RACK CONTEXT
     ↓
HAND–OBJECT INTERACTION
     ↓
TEMPORAL ACTION RECOGNITION
     ↓
ACTION EVENT
     ↓
CONFIDENCE
     ↓
PROTOCOL ENGINE
```

---

## 1. Input

Input can be:
* USB camera
* RTSP stream
* recorded video
* synthetic/test video

M2 should work with a standard frame interface rather than depending on one camera implementation.

Example:
```python
frame = camera.read()
```
M2 should not care whether that frame came from USB, RTSP or a recorded file.

---

# 2. Object detection

Primary model:
**YOLO-family lightweight model** such as YOLOv8n/YOLO11n, depending on benchmarking.

Initial object classes should be limited to the selected experiment.

Example:
```text
astronaut
tube_A
tube_B
pipette
cap
tray
rack
```

The model must return:
```python
Detection(
    class_name,
    confidence,
    bbox
)
```

Do **not** create dozens of classes just to make the model look sophisticated.
The hackathon MVP should prioritize **reliable detection of the objects needed for the chosen experiment**.

---

# 3. Pose + hands

Use pose/hand landmarks to understand **how the astronaut interacts with objects**.

Recommended:
```text
MediaPipe Pose
MediaPipe Hands
```

The important output isn't simply:
> "Astronaut detected."

It should provide information such as:
```text
left hand position
right hand position
body landmarks
distance from hand → object
```
This information is later used to infer actions.

---

# 4. Tracking

Detections from individual frames aren't enough. We need persistent identities:
```text
Frame 1 → Tube_A = ID 7
Frame 2 → Tube_A = ID 7
Frame 3 → Tube_A = ID 7
```

Use: **ByteTrack or BoT-SORT**

The purpose is to maintain object/person identity and movement over time.

M2 should expose a clean tracking output such as:
```python
Track(
    track_id,
    class_name,
    bbox,
    confidence
)
```

---

# 5. Spatial context

The system should eventually understand objects **relative to the payload/rack**, rather than relying on an assumed Earth-style floor/up/down orientation.

Preferred implementation: **ArUco-based rack reference frame**

Example:
```text
Camera coordinates → ArUco calibration → Rack-relative coordinates → Rack zone
```

Example output:
```python
object.zone = "A2"
```
This layer belongs logically between tracking and action recognition. M2 should design action recognition so that it can consume spatial information, but **M2 should not hardcode the rack/protocol rules**.

---

# 6. Hand–object interaction

This is a key part of M2's work. The system must distinguish:
```text
hand near tube
```
from:
```text
hand actually picked up tube
```

Possible signals:
```text
distance between hand and object + relative movement + object movement + hand/object persistence + pose
```

Example:
```text
Hand approaches Tube A → Hand touches Tube A → Tube A moves with hand → PICK(Tube_A)
```
This interaction layer should generate candidate actions.

---

# 7. Temporal action recognition

**Do NOT classify actions from a single frame.** Actions happen across multiple frames.

Example:
```text
t1 hand approaches tube
t2 hand contacts tube
t3 tube begins moving
t4 tube follows hand
        ↓
     PICK_TUBE
```

Therefore M2 needs a temporal buffer. For the first version, a **rule-based temporal buffer** is preferable to immediately building a complicated transformer.

Priority:
```text
Reliable temporal rules > Complex model with poor reliability
```

---

# 8. Standard action vocabulary

For the first experiment, define a small controlled action vocabulary, for example:
```text
IDENTIFY
PICK
OPEN
TRANSFER
SEAL
PLACE
```
The exact actions should match the selected experiment protocol. M2 should **not invent new action names independently**. Action labels must be agreed with M3/protocol owner.

---

# 9. M2's most important output: `ActionEvent`

M2 should NOT send raw YOLO detections directly to the protocol engine. Instead, convert perception into a standardized event:

```json
{
  "action": "PICK",
  "object": "tube_A",
  "actor": "astronaut_01",
  "timestamp": 12.43,
  "confidence": 0.93,
  "rack_zone": "A2"
}
```
This is the **interface between M2 and the protocol engine**.

---

# 10. Confidence and uncertainty

Every meaningful AI event must have a confidence score.
If the evidence is weak:
```text
PICK Tube A (confidence = 0.51)
```
M2 should report uncertainty (`CONFIRMED` / `UNCERTAIN`) instead of forcing a classification.

---

# 11. Edge deployment optimization

Must run locally/offline on hardware-agnostic targets (Laptop/Desktop, Raspberry Pi, RK3588 SBC, etc. - do not make code CUDA/Jetson-dependent).

Preferred approach:
```text
lightweight YOLO + tracking between detections + pose/hands when useful + temporal buffering
```

---

# 12. M2's folder ownership

```text
src/
├── perception/
│   ├── objects.py
│   ├── pose.py
│   └── hands.py
├── tracking/
│   └── track.py
├── spatial/
│   └── rack_mapping.py
└── actions/
    ├── recognizer.py
    └── event.py

models/
└── yolo/
```

---

# 13. What M2 should NOT build

```text
❌ protocol state machine
❌ FastAPI
❌ Streamlit UI
❌ TTS
❌ database
❌ experiment progression
❌ alert logic
```

---

# 14. Development order for M2

```text
1. Get camera frames
2. YOLO detection
3. Pose + hands
4. Tracking
5. Hand–object interaction
6. Basic actions
7. Temporal action recognition
8. Rack-relative context
9. Confidence/uncertainty
10. ActionEvent API
```

---

# 15. Success criterion

Convert raw video into reliable, timestamped, spatially-aware, confidence-scored action events — without deciding whether those actions are procedurally correct.
