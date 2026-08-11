"""Logging facade and step formatting utilities for the simulation engine."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable


class EventLogger:
    """Minimal logging facade isolating simulation engine from output handlers.

    Attributes:
        verbose (bool): Controls whether diagnostic log messages are emitted.
    """

    def __init__(
        self, verbose: bool = True, logger: logging.Logger | None = None
    ):
        """Initializes EventLogger with verbosity level and optional logger.

        Args:
            verbose (bool): Enables log output if True. Defaults to True.
            logger (Optional[logging.Logger]): Underlying Python logger
                instance.
        """
        self.verbose = verbose
        self._logger = logger or logging.getLogger(__name__)

    def log(self, message: str) -> None:
        """Emits an informational log message if verbosity is enabled.

        Args:
            message (str): Log message string.
        """
        if self.verbose:
            self._logger.info(message)

    def log_step_summary(self, step_data: Dict[str, Any]) -> None:
        """Formats and logs a step summary payload.

        Args:
            step_data (Dict[str, Any]): Step frame dictionary.
        """
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
            msg = (
                f"{status.get('name', 'Inconnu')} pos=({x:.2f}, {y:.2f}) "
                f"vitalite={vitality:.0f} faim={hunger:.0f} "
                f"soif={thirst:.0f} fatigue={fatigue:.0f}{calories_fragment}"
            )
            fragments.append(msg)

        details = " | ".join(fragments) if fragments else "aucune espece"
        self.log(f"\nStep {step_data.get('step', '?')} : {details}")
