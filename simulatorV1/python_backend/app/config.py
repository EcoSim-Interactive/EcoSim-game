"""Configuration applicative partagee entre la CLI et le serveur."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationSettings:
    """Regroupe les parametres d'execution de la simulation."""

    steps: int = 1000
    verbose: bool = True
    write_logs: bool = False
    logs_dir: str = "logs"
    tick_ms: int = 50
    host: str = "localhost"
    port: int = 8765
    port_scan_limit: int = 5  # Nombre de ports consecutifs testes si le port principal est occupe.
    world_config_path: str = "world_config.json"
    seed: Optional[int] = None


DEFAULT_SETTINGS = SimulationSettings()
