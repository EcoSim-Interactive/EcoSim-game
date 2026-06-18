"""Outils de journalisation specialises pour les runs de simulation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable


class EventLogger:
    """Facade minimale de logging pour isoler le moteur de la sortie console."""  # noqa: E501

    def __init__(
        self, verbose: bool = True, logger: logging.Logger | None = None
    ):
        self.verbose = verbose
        self._logger = logger or logging.getLogger(__name__)

    def log(self, message: str) -> None:
        if self.verbose:
            self._logger.info(message)

    def log_step_summary(self, step_data: Dict[str, Any]) -> None:
        if not self.verbose or not step_data:
            return

        species_states: Iterable[Dict[str, Any]] = step_data.get("species", [])
        fragments = []
        for status in species_states:
            after = status.get("after") or {}
            before = status.get("before") or {}
            x = after.get("x", before.get("x", 0.0))
            y = after.get("y", before.get("y", 0.0))
            vitality = after.get("vitality", before.get("vitality", 0))
            calories = after.get("calories", before.get("calories"))
            hunger = after.get("hunger", before.get("hunger", 0))
            thirst = after.get("thirst", before.get("thirst", 0))
            fatigue = after.get("fatigue", before.get("fatigue", 0))
            calories_fragment = (
                f" calories={calories:.0f}"
                if isinstance(calories, (int, float))
                else ""
            )
            fragments.append(
                f"{status.get('name', 'Inconnu')} pos=({x:.2f}, {y:.2f}) vitalite={vitality:.0f} faim={hunger:.0f} soif={thirst:.0f} fatigue={fatigue:.0f}{calories_fragment}"  # noqa: E501
            )

        details = " | ".join(fragments) if fragments else "aucune espece"
        self.log(f"\nStep {step_data.get('step', '?')} : {details}")
