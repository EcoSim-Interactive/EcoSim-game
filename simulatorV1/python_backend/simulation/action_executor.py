"""Execution helpers for simulation actions."""
from __future__ import annotations

from typing import Any, Callable, Dict

LogFn = Callable[[str], None]


def resolve_consumption(world: Any, species: Any, log: LogFn) -> Dict[str, Any]:
    """Check whether the species has eaten after completing its action."""
    result = species.try_eat(world)
    if result and result.get("consumed", 0.0) > 0.0:
        log(f"{species.name} a mange {result['consumed']:.1f} unites de nourriture.")
        return {"action_suffix": "_and_ate", "food_event": result}
    return {"action_suffix": "", "food_event": None}
