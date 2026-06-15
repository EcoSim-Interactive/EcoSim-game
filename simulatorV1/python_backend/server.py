"""Point d'entree de compatibilite pour lancer le serveur WebSocket."""
from __future__ import annotations

import asyncio
import logging

from infrastructure.http.server import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    asyncio.run(main())
