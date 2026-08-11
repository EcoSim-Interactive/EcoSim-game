"""Utility helpers for finalizing entity action resolution in simulation."""

from __future__ import annotations

from typing import Any, Callable, Dict

LogFn = Callable[[str], None]


def resolve_consumption(
    world: Any, species: Any, log: LogFn
) -> Dict[str, Any]:
    """Verifies whether current action leads the entity to consume food.

    Args:
        world (Any): World environment containing food sources.
        species (Any): Acting species/animal instance.
        log (LogFn): Logger callback function.

    Returns:
        Dict[str, Any]: Resolution payload containing action suffix and event.
    """
    result = species.try_eat(world)
    if result and result.get("consumed", 0.0) > 0.0:
        log(f"{species.name} a mange {result['consumed']:.1f} calories.")
        return {"action_suffix": "_and_ate", "food_event": result}
    return {"action_suffix": "", "food_event": None}
