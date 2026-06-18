"""Comportements de charognage pour les carnivores opportunistes."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from domain.constants import (
    CARNIVORE_EAT_DISTANCE,
    HUNGER_CRITICAL_FEED_OVERRIDE,
    SCAVENGE_WAIT_LIMIT_STEPS,
)

from ..animal import Animal

SCAVENGE_FAIL_LIMIT = 4
SCAVENGE_BLOCK_TTL = 48


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


def _state_set(state: Dict[str, Any], key: str) -> Set[Any]:
    stored = state.get(key)
    if isinstance(stored, set):
        return stored
    normalized = set(stored or [])
    state[key] = normalized
    return normalized


def _find_shared_kill(animal: Animal) -> Optional[Dict[str, object]]:
    scavenger_cfg = animal.get_trait("scavenger", {})
    follow_packs = (
        scavenger_cfg.get("follow_packs")
        if isinstance(scavenger_cfg, dict)
        else None
    )
    if not follow_packs:
        return None
    for pack_id in follow_packs:
        shared = Animal.pack_state_for(str(pack_id)).get("shared_kill")
        if shared:
            return shared
    return None


def _scavenge_memory(animal: Animal) -> Dict[str, Any]:
    state = (
        animal.recall_social("scavenge_memory", {})
        if hasattr(animal, "recall_social")
        else {}
    )
    if not isinstance(state, dict):
        state = {}
    if hasattr(animal, "remember_social"):
        animal.remember_social("scavenge_memory", state)
    return state


def _tick_blocked_foods(animal: Animal) -> Dict[str, int]:
    state = _scavenge_memory(animal)
    blocked = state.setdefault("blocked_food_ids", {})
    expired = []
    for food_id, ttl in list(blocked.items()):
        remaining = int(ttl) - 1
        if remaining <= 0:
            expired.append(food_id)
        else:
            blocked[food_id] = remaining
    for food_id in expired:
        blocked.pop(food_id, None)
    return blocked


def _clear_failure(animal: Animal, food_id: Optional[str]) -> None:
    if not food_id:
        return
    state = _scavenge_memory(animal)
    state.setdefault("approach_failures", {}).pop(food_id, None)
    state.setdefault("blocked_food_ids", {}).pop(food_id, None)


def _register_failure(animal: Animal, food_id: Optional[str]) -> bool:
    if not food_id:
        return False
    state = _scavenge_memory(animal)
    failures = state.setdefault("approach_failures", {})
    count = int(failures.get(food_id, 0)) + 1
    failures[food_id] = count
    if count < SCAVENGE_FAIL_LIMIT:
        return False
    failures.pop(food_id, None)
    state.setdefault("blocked_food_ids", {})[food_id] = SCAVENGE_BLOCK_TTL
    return True


def _handle_failed_approach(
    animal: Animal,
    world,
    *,
    food_id: Optional[str],
    action: str,
    shared_kill: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, bool]:
    permanently_blocked = _register_failure(animal, food_id)
    if permanently_blocked and shared_kill is not None:
        blocked = _state_set(shared_kill, "blocked")
        blocked.add(animal.animal_id)
        participants = shared_kill.get("participants")
        if (
            isinstance(participants, dict)
            and participants
            and blocked.issuperset(participants.keys())
        ):
            shared_kill.clear()
    if permanently_blocked:
        return False, "", False
    if animal.random_move(world):
        return True, action, False
    return False, "", False


def _nearest_unblocked_carcass(
    animal: Animal, world, blocked_food_ids: Set[str]
) -> Optional[Dict[str, Any]]:
    if not hasattr(world, "food_sources"):
        return None
    candidates = [
        food
        for food in world.food_sources
        if food.get("id") not in blocked_food_ids
        and (
            not hasattr(world, "food_has_supply")
            or world.food_has_supply(food)
        )
        and (
            not hasattr(world, "food_matches_diet")
            or world.food_matches_diet(food, animal.diet)
        )
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda food: animal.distance_to(food))


def seek_carcass_opportunity(
    animal: Animal,
    world,
    *,
    hunger_threshold: float = 45.0,
) -> Tuple[bool, str, bool]:
    """Dirige un charognard vers une carcasse en respectant
    les priorites de nourrissage.
    """
    scavenger_cfg = animal.get_trait("scavenger", {})
    if not isinstance(scavenger_cfg, dict):
        return False, "", False

    if animal.hunger < float(
        scavenger_cfg.get("hunger_threshold", hunger_threshold)
    ):
        return False, "", False

    blocked_food_ids = set(_tick_blocked_foods(animal).keys())
    shared_kill = _find_shared_kill(animal)
    wait_priorities = _priority_set(scavenger_cfg.get("wait_for_priorities"))
    wait_distance = float(
        scavenger_cfg.get("wait_distance", animal.vision * 0.8)
    )

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
                if (
                    carcass is not None
                    and hasattr(world, "food_has_supply")
                    and not world.food_has_supply(carcass)
                ):
                    carcass = None
            if carcass is None:
                return False, "", False
            food_id = carcass.get("id")
            if food_id in blocked_food_ids:
                blocked = _state_set(shared_kill, "blocked")
                blocked.add(animal.animal_id)
                return False, "", False
            target_point = {
                "x": float(carcass.get("x", location[0])),
                "y": float(carcass.get("y", location[1])),
            }
            distance = animal.distance_to(target_point)
            participants = shared_kill.get("participants")
            if not isinstance(participants, dict):
                participants = {}
            blocked = _state_set(shared_kill, "blocked")
            fed_animals = _state_set(shared_kill, "fed_animals")
            wait_counters = shared_kill.setdefault("scavenge_wait", {})
            force_feed = animal.hunger >= HUNGER_CRITICAL_FEED_OVERRIDE
            pending_required = [
                member_id
                for member_id, priority in participants.items()
                if priority in wait_priorities
                and member_id not in fed_animals
                and member_id not in blocked
            ]

            if pending_required and not force_feed:
                wait_count = int(wait_counters.get(animal.animal_id, 0)) + 1
                wait_counters[animal.animal_id] = wait_count
                if wait_count <= SCAVENGE_WAIT_LIMIT_STEPS:
                    if distance > wait_distance:
                        if animal.move_towards(target_point, world):
                            _clear_failure(animal, food_id)
                            return True, "scavenge_move_wait_zone", False
                        return _handle_failed_approach(
                            animal,
                            world,
                            food_id=food_id,
                            action="scavenge_reposition",
                            shared_kill=shared_kill,
                        )
                    return True, "scavenge_hold_position", False
                force_feed = True

            if force_feed:
                wait_counters[animal.animal_id] = 0

            if distance > CARNIVORE_EAT_DISTANCE:
                if animal.move_towards(target_point, world):
                    _clear_failure(animal, food_id)
                    return True, "scavenge_move_to_carcass", False
                return _handle_failed_approach(
                    animal,
                    world,
                    food_id=food_id,
                    action="scavenge_reposition",
                    shared_kill=shared_kill,
                )
            _clear_failure(animal, food_id)
            return True, "scavenge_feed_on_shared", True

    detection_range = float(scavenger_cfg.get("range", animal.vision))
    carcass = _nearest_unblocked_carcass(animal, world, blocked_food_ids)
    if not carcass:
        return False, "", False

    food_id = carcass.get("id")
    distance = animal.distance_to(carcass)
    if distance > detection_range:
        return False, "", False

    if distance > animal.vision:
        if animal.move_towards(carcass, world):
            _clear_failure(animal, food_id)
            return True, "scavenge_follow_scent", False
        return _handle_failed_approach(
            animal,
            world,
            food_id=food_id,
            action="scavenge_reposition",
        )

    if not animal.move_towards(carcass, world):
        return _handle_failed_approach(
            animal,
            world,
            food_id=food_id,
            action="scavenge_reposition",
        )
    _clear_failure(animal, food_id)
    resolve = distance <= CARNIVORE_EAT_DISTANCE
    return (
        True,
        "scavenge_consume" if resolve else "scavenge_approach",
        resolve,
    )
