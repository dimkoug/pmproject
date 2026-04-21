import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.websockets.manager import ConnectionManager


class TestConnectionManagerInit:
    def test_init_empty(self):
        mgr = ConnectionManager()
        assert mgr.active_connections == {}

    def test_init_no_connections_for_project(self):
        mgr = ConnectionManager()
        assert "nonexistent" not in mgr.active_connections


class TestConnectionManagerConnect:
    async def test_connect_adds_to_list(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "project-1")
        assert "project-1" in mgr.active_connections
        assert ws in mgr.active_connections["project-1"]
        ws.accept.assert_called_once()

    async def test_connect_multiple_to_same_project(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-1")
        assert len(mgr.active_connections["project-1"]) == 2

    async def test_connect_different_projects(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-2")
        assert len(mgr.active_connections) == 2
        assert ws1 in mgr.active_connections["project-1"]
        assert ws2 in mgr.active_connections["project-2"]


class TestConnectionManagerDisconnect:
    async def test_disconnect_removes_from_list(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "project-1")
        mgr.disconnect(ws, "project-1")
        assert "project-1" not in mgr.active_connections

    async def test_disconnect_one_of_multiple(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-1")
        mgr.disconnect(ws1, "project-1")
        assert len(mgr.active_connections["project-1"]) == 1
        assert ws2 in mgr.active_connections["project-1"]

    async def test_disconnect_last_removes_project_key(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "project-1")
        mgr.disconnect(ws, "project-1")
        assert "project-1" not in mgr.active_connections

    def test_disconnect_nonexistent_project(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        # Should not raise
        mgr.disconnect(ws, "nonexistent")


class TestConnectionManagerBroadcast:
    async def test_broadcast_sends_to_all_in_project(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-1")

        await mgr.broadcast("project-1", "task_created", {"id": "1", "title": "Test"})

        expected = json.dumps({"event": "task_created", "data": {"id": "1", "title": "Test"}})
        ws1.send_text.assert_called_once_with(expected)
        ws2.send_text.assert_called_once_with(expected)

    async def test_broadcast_only_to_correct_project(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-2")

        await mgr.broadcast("project-1", "task_created", {"id": "1"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()

    async def test_broadcast_no_connections(self):
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast("nonexistent", "event", {"key": "value"})

    async def test_broadcast_handles_send_error(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws1.send_text.side_effect = Exception("Connection closed")
        ws2 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-1")

        # Should not raise, and ws2 should still receive
        await mgr.broadcast("project-1", "event", {"data": "test"})
        ws2.send_text.assert_called_once()

    async def test_broadcast_message_format(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        await mgr.broadcast("p1", "risk_updated", {"id": "r1", "status": "resolved"})

        call_args = ws.send_text.call_args[0][0]
        parsed = json.loads(call_args)
        assert parsed["event"] == "risk_updated"
        assert parsed["data"]["id"] == "r1"
        assert parsed["data"]["status"] == "resolved"


class TestConnectionManagerBroadcastAll:
    async def test_broadcast_all_sends_to_all_projects(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        await mgr.connect(ws1, "project-1")
        await mgr.connect(ws2, "project-2")
        await mgr.connect(ws3, "project-2")

        await mgr.broadcast_all("project_created", {"id": "new", "name": "New"})

        expected = json.dumps({"event": "project_created", "data": {"id": "new", "name": "New"}})
        ws1.send_text.assert_called_once_with(expected)
        ws2.send_text.assert_called_once_with(expected)
        ws3.send_text.assert_called_once_with(expected)

    async def test_broadcast_all_no_connections(self):
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast_all("event", {"key": "value"})

    async def test_broadcast_all_handles_errors(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws1.send_text.side_effect = Exception("Closed")
        ws2 = AsyncMock()
        await mgr.connect(ws1, "p1")
        await mgr.connect(ws2, "p2")

        await mgr.broadcast_all("event", {"data": "test"})
        ws2.send_text.assert_called_once()


class TestBroadcastEventTypes:
    """Test that various PMBOK event types can be broadcast correctly."""

    async def test_task_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        for event in ["task_created", "task_updated", "task_deleted"]:
            ws.reset_mock()
            await mgr.broadcast("p1", event, {"id": "t1"})
            msg = json.loads(ws.send_text.call_args[0][0])
            assert msg["event"] == event

    async def test_risk_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        for event in ["risk_created", "risk_updated", "risk_deleted"]:
            ws.reset_mock()
            await mgr.broadcast("p1", event, {"id": "r1"})
            msg = json.loads(ws.send_text.call_args[0][0])
            assert msg["event"] == event

    async def test_stakeholder_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        for event in ["stakeholder_created", "stakeholder_updated", "stakeholder_deleted"]:
            ws.reset_mock()
            await mgr.broadcast("p1", event, {"id": "s1"})
            msg = json.loads(ws.send_text.call_args[0][0])
            assert msg["event"] == event

    async def test_deliverable_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        for event in ["deliverable_created", "deliverable_updated", "deliverable_deleted"]:
            ws.reset_mock()
            await mgr.broadcast("p1", event, {"id": "d1"})
            msg = json.loads(ws.send_text.call_args[0][0])
            assert msg["event"] == event

    async def test_measurement_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        await mgr.broadcast("p1", "measurement_created", {"id": "m1", "name": "SPI"})
        msg = json.loads(ws.send_text.call_args[0][0])
        assert msg["event"] == "measurement_created"
        assert msg["data"]["name"] == "SPI"

    async def test_change_request_events(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        await mgr.broadcast("p1", "change_request_updated", {"id": "cr1", "status": "approved"})
        msg = json.loads(ws.send_text.call_args[0][0])
        assert msg["event"] == "change_request_updated"
        assert msg["data"]["status"] == "approved"

    async def test_project_events_broadcast_all(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws, "p1")

        await mgr.broadcast_all("project_created", {"id": "p-new", "name": "New PMBOK Project"})
        msg = json.loads(ws.send_text.call_args[0][0])
        assert msg["event"] == "project_created"
        assert msg["data"]["name"] == "New PMBOK Project"


class TestHealthEndpoint:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
