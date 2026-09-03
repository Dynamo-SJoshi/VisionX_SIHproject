"""
Integration tests for FastAPI REST endpoints and WebSocket telemetry routes.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.routes import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestAPI:

    def test_health_check(self, client: TestClient):
        """Verify /api/v1/health returns healthy status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "HEALTHY"
        assert "protocol_loaded" in data

    def test_get_protocol(self, client: TestClient):
        """Verify /api/v1/protocol returns current active protocol and state."""
        response = client.get("/api/v1/protocol")
        assert response.status_code == 200
        data = response.json()
        assert "current_step_id" in data
        assert "expected_action" in data

    def test_session_lifecycle(self, client: TestClient):
        """Verify starting and stopping a session."""
        start_res = client.post(
            "/api/v1/session/start",
            json={"session_id": "EXP_TEST_001", "experiment_id": "sample_transfer_v1"},
        )
        assert start_res.status_code == 200
        assert start_res.json()["session_id"] == "EXP_TEST_001"

        stop_res = client.post("/api/v1/session/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "SESSION_STOPPED"

    def test_action_ingestion_valid(self, client: TestClient):
        """Verify ingesting a valid action advances the protocol."""
        client.post("/api/v1/protocol/reset")

        action_payload = {
            "event_id": "evt_api_s1",
            "session_id": "EXP_TEST_001",
            "sequence_number": 1,
            "actor_id": "astronaut_01",
            "action": "identify",
            "confidence": 0.95,
            "status": "validated",
            "target_object": {
                "object_id": "tube_A",
                "object_label": "sample_tube",
                "role": "target",
                "confidence": 0.95,
            },
            "interaction_zone": "WORKBENCH",
        }

        res = client.post("/api/v1/action", json=action_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["validation"]["status"] == "valid"
        assert data["decision"]["status"] == "proceed"
        assert data["decision"]["protocol_advances"] is True

    def test_action_ingestion_violation(self, client: TestClient):
        """Verify ingesting an out-of-order action triggers violation alert."""
        client.post("/api/v1/protocol/reset")

        action_payload = {
            "event_id": "evt_api_violation",
            "session_id": "EXP_TEST_001",
            "sequence_number": 2,
            "actor_id": "astronaut_01",
            "action": "open",
            "confidence": 0.92,
            "status": "validated",
            "target_object": {
                "object_id": "tube_A",
                "role": "target",
                "confidence": 0.92,
            },
            "interaction_zone": "WORKBENCH",
        }

        res = client.post("/api/v1/action", json=action_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["validation"]["status"] == "invalid"
        assert data["decision"]["status"] == "alert"
        assert data["decision"]["requires_attention"] is True
        assert "Procedure warning" in data["decision"]["voice_message"]

    def test_manual_confirm(self, client: TestClient):
        """Verify astronaut manual step confirmation override."""
        client.post("/api/v1/protocol/reset")

        confirm_res = client.post(
            "/api/v1/confirm",
            json={"step_id": "S1", "astronaut_id": "astronaut_01", "notes": "Visual occlusion verified"},
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["status"] == "CONFIRMED"

    def test_get_telemetry_snapshot(self, client: TestClient):
        """Verify /api/v1/telemetry returns full telemetry contract matching M5 schema."""
        res = client.get("/api/v1/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert "timestamp" in data
        assert "session_id" in data
        assert "progress_percentage" in data
        assert "protocol_steps" in data
        assert "status" in data
        assert "system_health" in data

    def test_websocket_telemetry(self, client: TestClient):
        """Verify WebSocket client connection and initial telemetry broadcast."""
        with client.websocket_connect("/ws/telemetry") as websocket:
            data = websocket.receive_json()
            assert "timestamp" in data
            assert "protocol_steps" in data
            assert "status" in data

            websocket.send_text("ping")
            reply = websocket.receive_text()
            assert reply == "pong"
