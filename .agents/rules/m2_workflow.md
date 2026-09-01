---
trigger: always_on
description: Fixed workflow rules and architecture boundaries for M2 — AI/Computer Vision Lead
---

# M2 — AI/Computer Vision Workflow Rules

M2 owns the AI perception and action-recognition pipeline for on-board BAS experiment tracking.

## Core Rules for M2
1. **Pipeline**: `Frame` → `Object Detection (YOLO)` → `Pose/Hands (YOLO-Pose/MediaPipe)` → `Tracker (ByteTrack/Dual-Stage)` → `Spatial Context (Dynamic Layout/ArUco)` → `Hand-Object Interaction` → `Temporal Action Buffer` → `ActionEvent`.
2. **Output Interface**: M2 must produce standardized `ActionEvent` JSON objects with confidence scores (e.g. `{"action": "PICK", "object": "tube_A", "actor": "astronaut_01", "timestamp": 12.43, "confidence": 0.93, "rack_zone": "A2"}`).
3. **Action Vocabulary**: Use agreed action names (`IDENTIFY`, `PICK`, `OPEN`, `TRANSFER`, `SEAL`, `PLACE`).
4. **Dynamic Rack Layout & Tools**:
   - Do NOT enforce hardcoded static rack slots. Support importing custom rack layouts externally via uploaded JPG reference images or JSON configs.
   - Experiments include diverse tools and instruments beyond test tubes (e.g. `screwdriver`, `wrench`, `syringe`, `multimeter`). The active tool vocabulary is dynamically configurable from the frontend / protocol definition.
5. **Edge First**: Keep models lightweight (YOLOv8n/11n), CPU/hardware-agnostic, and offline-ready. Do not depend on CUDA/Jetson-only APIs.
6. **Boundaries**: Do NOT build protocol state machines, UI, FastAPI endpoints, TTS, or alert logic.
