"""Scavenging behaviours for opportunistic carnivores."""
from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from ..animal import Animal
from domain.constants import (
    CARNIVORE_EAT_DISTANCE,
    HUNGER_CRITICAL_FEED_OVERRIDE,
    SCAVENGE_WAIT_LIMIT_STEPS,
)


def _priority_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _priority_set(value: Any) -> Set[float]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {_priority_value(item, 0.0) for item in value}
    return {_priority_value(value, 0.0)}


def _find_shared_kill(animal: Animal) -> Optional[Dict[str, object]]:
    scavenger_cfg = animal.get_trait("scavenger", {})
    follow_packs = scavenger_cfg.get("follow_packs") if isinstance(scavenger_cfg, dict) else None
    if not follow_packs:
        return None
    for pack_id in follow_packs:
        shared = Animal.pack_state_for(str(pack_id)).get("shared_kill")
        if shared:
            return shared
    return None


def seek_carcass_opportunity(
    animal: Animal,
    world,
    *,
    hunger_threshold: float = 45.0,
) -> Tuple[bool, str, bool]:
    """Drive scavengers towards carcasses while respecting feeding priority."""
    scavenger_cfg = animal.get_trait("scavenger", {})
    if not isinstance(scavenger_cfg, dict):
        return False, "", False

    if animal.hunger < float(scavenger_cfg.get("hunger_threshold", hunger_threshold)):
        return False, "", False

    shared_kill = _find_shared_kill(animal)
    wait_priorities = _priority_set(scavenger_cfg.get("wait_for_priorities"))
    wait_distance = float(scavenger_cfg.get("wait_distance", animal.vision * 0.8))

    if shared_kill:
        location = shared_kill.get("position")
        if isinstance(location, (list, tuple)) and len(location) >= 2:
            food_id = shared_kill.get("food_id")
            carcass = None
            if food_id and hasattr(world, "food_sources"):
                for food in world.food_sources:
                    if food.get("id") == food_id:
                        carcass = food
                        break
                if carcass is not None and hasattr(world, "food_has_supply") and not world.food_has_supply(carcass):
                    carcass = None
            if carcass is None:
                return False, "", False
            target_point = {"x": float(carcass.get("x", location[0])), "y": float(carcass.get("y", location[1]))}
            distance = animal.distance_to(target_point)
            if world is not None and hasattr(world, "_line_blocked_by_water"):
                if world._line_blocked_by_water(
                    int(round(animal.x)),
                    int(round(animal.y)),
                    int(round(target_point["x"])),
                    int(round(target_point["y"])),
                ):
                    return False, "", False
            stored_fed = shared_kill.get("fed_priorities")
            if isinstance(stored_fed, set):
                fed_priorities = stored_fed
            else:
                fed_priorities = set(stored_fed or [])

            wait_counters = shared_kill.setdefault("scavenge_wait", {})
            force_feed = animal.hunger >= HUNGER_CRITICAL_FEED_OVERRIDE

            if wait_priorities and not wait_priorities.issubset(fed_priorities) and not force_feed:
                wait_count = int(wait_counters.get(animal.animal_id, 0)) + 1
                wait_counters[animal.animal_id] = wait_count
                if wait_count <= SCAVENGE_WAIT_LIMIT_STEPS:
                    if distance > wait_distance:
                        animal.move_towards(target_point, world)
                        return True, "scavenge_move_wait_zone", False
                    return True, "scavenge_hold_position", False
                force_feed = True

            if force_feed:
                wait_counters[animal.animal_id] = 0

            if distance > CARNIVORE_EAT_DISTANCE:
                animal.move_towards(target_point, world)
                return True, "scavenge_move_to_carcass", False
            return True, "scavenge_feed_on_shared", True

    detection_range = float(scavenger_cfg.get("range", animal.vision))
    carcass = world.get_nearest_food(animal.x, animal.y, diet=animal.diet)
    if not carcass:
        return False, "", False

    distance = animal.distance_to(carcass)
    if world is not None and hasattr(world, "_line_blocked_by_water"):
        if world._line_blocked_by_water(
            int(round(animal.x)),
            int(round(animal.y)),
            int(round(carcass.get("x", 0.0))),
            int(round(carcass.get("y", 0.0))),
        ):
            return False, "", False
    if distance > detection_range:
        return False, "", False

    if distance > animal.vision:
        animal.move_towards(carcass, world)
        return True, "scavenge_follow_scent", False

    animal.move_towards(carcass, world)
    resolve = distance <= CARNIVORE_EAT_DISTANCE
    return True, "scavenge_consume" if resolve else "scavenge_approach", resolve
