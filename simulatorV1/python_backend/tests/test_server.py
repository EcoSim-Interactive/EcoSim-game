"""Tests for the WebSocket command handling in the HTTP server."""

import json
import unittest
from unittest.mock import AsyncMock

from infrastructure.http.server import (
    _reset_runtime_state,
    handle_command,
)


class TestWebSocketServer(unittest.IsolatedAsyncioTestCase):
    """Tests for the WebSocket command handlers."""

    def setUp(self):
        """Reset runtime state and set up a mocked websocket client."""
        _reset_runtime_state()
        self.mock_ws = AsyncMock()
        # Mock the remote_address to prevent errors if the server logs it
        self.mock_ws.remote_address = ("127.0.0.1", 12345)

    async def test_handle_unknown_command(self):
        """Verify an unrecognized command replies with an error
        message.
        """
        await handle_command(self.mock_ws, '{"cmd": "unknown_cmd"}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "error")
        self.assertEqual(sent_data["message"], "Unknown command")

    async def test_speed_command_valid(self):
        """Verify a positive speed value replies with the updated
        status.
        """
        await handle_command(self.mock_ws, '{"cmd": "speed", "value": 50}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "status")
        self.assertEqual(sent_data["data"], "speed=50ms")

    async def test_speed_command_invalid(self):
        """Verify a negative speed value is rejected with an error
        message.
        """
        await handle_command(self.mock_ws, '{"cmd": "speed", "value": -10}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "error")
        self.assertEqual(sent_data["message"], "invalid speed")

    async def test_pause_command(self):
        """Verify the pause command replies with a paused status."""
        await handle_command(self.mock_ws, '{"cmd": "pause"}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "status")
        self.assertEqual(sent_data["data"], "paused")

    async def test_resume_command(self):
        """Verify the resume command replies with a resumed status."""
        await handle_command(self.mock_ws, '{"cmd": "resume"}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "status")
        self.assertEqual(sent_data["data"], "resumed")

    async def test_stop_command(self):
        """Verify the stop command replies with a stopped status."""
        await handle_command(self.mock_ws, '{"cmd": "stop"}')
        self.mock_ws.send.assert_awaited_once()
        sent_data = json.loads(self.mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["type"], "status")
        self.assertEqual(sent_data["data"], "stopped")


if __name__ == "__main__":
    unittest.main()
