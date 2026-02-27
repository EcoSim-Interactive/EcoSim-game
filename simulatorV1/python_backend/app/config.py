"""Application level configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationSettings:
    steps: int = 2000
    verbose: bool = True
    write_logs: bool = False
    logs_dir: str = "logs"
    tick_ms: int = 50
    host: str = "localhost"
    port: int = 8765
    port_scan_limit: int = 5  # number of incremental ports to try when busy
    world_config_path: str = "world_config.json"


DEFAULT_SETTINGS = SimulationSettings()
