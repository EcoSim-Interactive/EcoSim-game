"""Application configuration models shared across server and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationSettings:
    """Dataclass encapsulating global simulation execution parameters.

    Attributes:
        steps (int): Total number of simulation steps. Defaults to 1000.
        verbose (bool): Controls if logging is enabled. Defaults to True.
        write_logs (bool): Persists JSON simulation logs to disk if True.
        logs_dir (str): Output log directory path. Defaults to "logs".
        tick_ms (int): Step streaming tick interval in ms. Defaults to 50.
        host (str): WebSocket network bind address. Defaults to "localhost".
        port (int): Primary WebSocket listening port. Defaults to 8765.
        port_scan_limit (int): Sequential port retry count if port in use.
        world_config_path (str): Path to JSON world config file.
        seed (Optional[int]): Random seed for reproducible generation.
    """

    steps: int = 1000
    verbose: bool = True
    write_logs: bool = False
    logs_dir: str = "logs"
    tick_ms: int = 50
    host: str = "localhost"
    port: int = 8765
    port_scan_limit: int = 5
    world_config_path: str = "world_config.json"
    seed: Optional[int] = None


DEFAULT_SETTINGS = SimulationSettings()
