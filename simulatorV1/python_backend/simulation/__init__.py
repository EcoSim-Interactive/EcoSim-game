"""API publique de la couche de simulation."""

from .engine import SimulationEngine

Simulation = (
    SimulationEngine  # Alias historique conserve pour limiter les regressions.
)

__all__ = ["SimulationEngine", "Simulation"]
