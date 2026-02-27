"""Backward compatible import shim for the WebSocket server."""
from __future__ import annotations

import asyncio
import logging

from infrastructure.http.server import main


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    asyncio.run(main())
