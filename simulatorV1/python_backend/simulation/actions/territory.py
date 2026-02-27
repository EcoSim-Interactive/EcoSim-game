"""Territory management utilities for territorial species."""
from __future__ import annotations

from typing import Dict, Tuple

from ..animal import Animal


def enforce_territory(
    animal: Animal,
    territory: Dict[str, object],
    world=None,
) -> Tuple[bool, str]:
    """Ensure the animal stays within its territory radius, patrolling if needed."""
    radius = float(territory.get("radius", 800.0))
    margin = float(territory.get("margin", radius * 0.15))
    center_raw = territory.get("center")
    if isinstance(center_raw, (list, tuple)) and len(center_raw) >= 2:
        center = {"x": float(center_raw[0]), "y": float(center_raw[1])}
    elif animal.territory_anchor:
        center = {"x": animal.territory_anchor[0], "y": animal.territory_anchor[1]}
    else:
        center = {"x": animal.x, "y": animal.y}

    distance = animal.distance_to(center)
    if distance > radius:
        animal.move_towards(center, world)
        return True, "territory_return"

    if distance > radius - margin:
        patrol_target = {
            "x": center["x"] + (animal.x - center["x"]) * 0.5,
            "y": center["y"] + (animal.y - center["y"]) * 0.5,
        }
        animal.move_towards(patrol_target, world)
        return True, "territory_patrol"

    return False, ""
