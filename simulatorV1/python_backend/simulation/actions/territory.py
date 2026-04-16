"""Gestion des deplacements lies au territoire des especes territoriales."""
from __future__ import annotations

from typing import Dict, Tuple

from ..animal import Animal


def enforce_territory(
    animal: Animal,
    territory: Dict[str, object],
    world=None,
) -> Tuple[bool, str]:
    """Force l'animal a rester dans son territoire ou a y revenir si besoin."""
    def _attempt_move(target: Dict[str, float], action: str) -> Tuple[bool, str]:
        if animal.move_towards(target, world):
            return True, action
        if animal.random_move(world):
            return True, "territory_reposition"
        return False, ""

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
        return _attempt_move(center, "territory_return")

    if distance > radius - margin:
        patrol_target = {
            "x": center["x"] + (animal.x - center["x"]) * 0.5,
            "y": center["y"] + (animal.y - center["y"]) * 0.5,
        }
        return _attempt_move(patrol_target, "territory_patrol")

    return False, ""
