"""Predation helpers reusable across cooperative carnivore species."""
from __future__ import annotations

import random
from typing import Any, Iterable, Optional, Set, Tuple

from ..animal import Animal
from domain.constants import (
    CARNIVORE_EAT_DISTANCE,
    HUNGER_CRITICAL_FEED_OVERRIDE,
    PACK_FEED_WAIT_LIMIT_STEPS,
    PACK_KILL_STALE_STEPS,
)


def _nearest_prey(
    animal: Animal,
    animals: Iterable[Animal],
    targets: Optional[Set[str]] = None,
    world: Any | None = None,
) -> Optional[Animal]:
    normalized_targets = {target.lower() for target in targets or set()}
    best: Optional[Animal] = None
    best_distance: Optional[float] = None
    for creature in animals:
        if creature is animal or not creature.alive:
            continue
        species_key = str(creature.species_type).lower()
        if creature.diet != "herbivore" and normalized_targets and species_key not in normalized_targets:
            continue
        if world is not None and hasattr(world, "_line_blocked_by_water"):
            if world._line_blocked_by_water(int(round(animal.x)), int(round(animal.y)), int(round(creature.x)), int(round(creature.y))):
                continue
        distance = animal.distance_to({"x": creature.x, "y": creature.y})
        if best_distance is None or distance < best_distance:
            best = creature
            best_distance = distance
    return best


def _priority_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _priority_set(value: Any) -> Set[float]:
    priorities: Set[float] = set()
    if value is None:
        return priorities
    if isinstance(value, (list, tuple, set)):
        for item in value:
            priorities.add(_priority_value(item, 0.0))
    else:
        priorities.add(_priority_value(value, 0.0))
    return {priority for priority in priorities if priority is not None}


def _should_coordinate(animal: Animal, hunt_cfg: dict[str, Any], role: str) -> bool:
    if hunt_cfg:
        return True
    if animal.get_trait("predator"):
        return True
    return role in {"hunter", "predator", "leader", "alpha"}


def _consume_carcass(animal: Animal, world, carcass_id: Optional[str]) -> float:
    if not carcass_id or not hasattr(world, "food_sources"):
        return 0.0
    carcass = None
    for food in world.food_sources:
        if food.get("id") == carcass_id:
            carcass = food
            break
    if carcass is None:
        return 0.0
    if hasattr(world, "food_has_supply") and not world.food_has_supply(carcass):
        return 0.0
    required = animal._compute_required_food_amount(carcass)
    result = world.consume_food(carcass, required) if hasattr(world, "consume_food") else None
    if not result or result.get("consumed", 0.0) <= 0.0:
        return 0.0
    consumed = float(result["consumed"])
    animal.consumed += 1
    animal.hunger = max(0.0, animal.hunger - consumed)
    animal.memory = None
    return consumed


def _handle_shared_kill(
    animal: Animal,
    pack_kill: dict[str, Any],
    feed_priority: float,
    wait_priorities: Set[float],
    approach_radius: float,
    guard_radius: float,
    world,
    log,
) -> Tuple[bool, str, bool]:
    location = pack_kill.get("position")
    if not isinstance(location, (list, tuple)) or len(location) < 2:
        return False, "", False

    food_id = pack_kill.get("food_id")
    carcass = None
    if food_id and hasattr(world, "food_sources"):
        for food in world.food_sources:
            if food.get("id") == food_id:
                carcass = food
                break
        if carcass is not None and hasattr(world, "food_has_supply") and not world.food_has_supply(carcass):
            carcass = None
    if carcass is None:
        # Carcass already consumed/removed, clear shared kill to allow new hunts.
        pack_kill.clear()
        return False, "", False

    target_point = {"x": float(carcass.get("x", location[0])), "y": float(carcass.get("y", location[1]))}
    distance = animal.distance_to(target_point)

    originator_id = pack_kill.get("originator")
    if animal.animal_id == originator_id:
        stale_steps = int(pack_kill.get("stale_steps", 0)) + 1
        pack_kill["stale_steps"] = stale_steps
        if stale_steps > PACK_KILL_STALE_STEPS:
            pack_kill.clear()
            return False, "", False

    participants = pack_kill.setdefault("participants", {})
    participants[animal.animal_id] = feed_priority

    blocked = pack_kill.setdefault("blocked", set())
    if animal.animal_id in blocked:
        if animal.animal_id == originator_id:
            pack_kill.clear()
        return False, "", False

    if distance > guard_radius and world is not None and hasattr(world, "_line_blocked_by_water"):
        if world._line_blocked_by_water(
            int(round(animal.x)),
            int(round(animal.y)),
            int(round(target_point["x"])),
            int(round(target_point["y"])),
        ):
            blocked.add(animal.animal_id)
            if blocked and participants and blocked.issuperset(participants.keys()):
                pack_kill.clear()
            return False, "", False

    if blocked and participants and blocked.issuperset(participants.keys()):
        pack_kill.clear()
        return False, "", False

    fed_priorities: Set[float] = pack_kill.setdefault("fed_priorities", set())
    wait_counters = pack_kill.setdefault("wait_counters", {})

    force_feed = animal.hunger >= HUNGER_CRITICAL_FEED_OVERRIDE

    def _blocked_after_move(previous: tuple[float, float]) -> bool:
        if world is None or not hasattr(world, "_line_blocked_by_water"):
            return False
        if world._line_blocked_by_water(
            int(round(previous[0])),
            int(round(previous[1])),
            int(round(target_point["x"])),
            int(round(target_point["y"])),
        ):
            blocked.add(animal.animal_id)
            return True
        return False

    if wait_priorities and not wait_priorities.issubset(fed_priorities) and not force_feed:
        wait_count = int(wait_counters.get(animal.animal_id, 0)) + 1
        wait_counters[animal.animal_id] = wait_count
        if wait_count <= PACK_FEED_WAIT_LIMIT_STEPS:
            if distance > guard_radius:
                previous = (animal.x, animal.y)
                animal.move_towards(target_point, world)
                if (animal.x, animal.y) == previous and _blocked_after_move(previous):
                    return False, "", False
                return True, "pack_waiting_move", False
            return True, "pack_waiting_guard", False
        force_feed = True

    if force_feed:
        wait_counters[animal.animal_id] = 0

    if feed_priority in fed_priorities and not force_feed:
        if distance > guard_radius:
            previous = (animal.x, animal.y)
            animal.move_towards(target_point, world)
            if (animal.x, animal.y) == previous and _blocked_after_move(previous):
                return False, "", False
            return True, "pack_guard_loop", False
        return True, "pack_guard_stand", False

    if distance > CARNIVORE_EAT_DISTANCE:
        previous = (animal.x, animal.y)
        animal.move_towards(target_point, world)
        if (animal.x, animal.y) == previous and _blocked_after_move(previous):
            return False, "", False
        return True, "pack_move_to_carcass", False

    fed_priorities.add(feed_priority)
    wait_counters[animal.animal_id] = 0
    pack_kill["stale_steps"] = 0
    pack_kill.setdefault("feed_log", []).append({"animal": animal.animal_id, "priority": feed_priority})
    log(f"{animal.name} consomme la carcasse partagee (priorite {feed_priority}).")
    animal.memory = target_point
    return True, "pack_feed_from_carcass", True


def execute_predation_cycle(
    animal: Animal,
    animals: Iterable[Animal],
    world,
    log,
) -> Tuple[bool, str, bool]:
    """Drive cooperative hunting, feeding order, and carcass sharing."""
    if animal.diet != "carnivore":
        return False, "", False

    raw_hunt_cfg = animal.get_trait("hunt")
    hunt_cfg: dict[str, Any] = raw_hunt_cfg if isinstance(raw_hunt_cfg, dict) else {}
    role = str(animal.get_trait("role", "")).lower()

    if not _should_coordinate(animal, hunt_cfg, role):
        return False, "", False

    attack_range = float(hunt_cfg.get("attack_range", max(40.0, animal.vision * 0.3)))
    chase_range = float(hunt_cfg.get("chase_range", max(animal.vision, attack_range * 2.0)))
    success_rate = float(hunt_cfg.get("success_rate", 0.5))
    pack_bonus = float(hunt_cfg.get("pack_bonus", 0.06))
    hunger_threshold = float(hunt_cfg.get("hunger_threshold", 55.0))
    approach_radius = float(hunt_cfg.get("feed_radius", attack_range))
    guard_radius = float(hunt_cfg.get("guard_radius", approach_radius * 1.25))

    if animal.pack_id and pack_bonus > 0:
        nearby = 0
        for other in animals:
            if other is animal or not other.alive:
                continue
            if other.pack_id != animal.pack_id:
                continue
            if animal.distance_to({"x": other.x, "y": other.y}) <= guard_radius:
                nearby += 1
        if nearby > 0:
            success_rate = min(0.95, success_rate + pack_bonus * nearby)

    feed_priority = _priority_value(
        animal.get_trait("feed_priority"),
        _priority_value(hunt_cfg.get("feed_priority"), 40.0 if role in {"leader", "alpha"} else 60.0),
    )
    wait_trait = animal.get_trait("wait_for_priorities")
    if wait_trait is None:
        wait_trait = hunt_cfg.get("wait_for_priorities")
    wait_priorities = _priority_set(wait_trait)

    raw_targets = hunt_cfg.get("targets")
    target_set = {str(value).lower() for value in raw_targets} if isinstance(raw_targets, (list, tuple, set)) else None

    pack_kill = animal.pack_state.get("shared_kill")
    if pack_kill:
        acted, action, resolve_food = _handle_shared_kill(
            animal,
            pack_kill,
            feed_priority,
            wait_priorities,
            approach_radius,
            guard_radius,
            world,
            log,
        )
        if acted:
            return True, action, resolve_food

    if animal.hunger < hunger_threshold:
        return False, "", False

    prey = _nearest_prey(animal, animals, target_set, world)
    if not prey:
        return False, "", False

    prey_point = {"x": prey.x, "y": prey.y}
    distance_to_prey = animal.distance_to(prey_point)

    if distance_to_prey > chase_range:
        animal.move_towards(prey_point, world)
        return True, "pack_tracking_prey", False

    if distance_to_prey > attack_range:
        animal.move_towards(prey_point, world)
        return True, "pack_closing_distance", False

    if random.random() > success_rate:
        animal.move_towards(prey_point, world)
        log(f"{animal.name} rate son attaque sur {prey.name}.")
        return True, "pack_attack_failed", False

    prey.vitality = 0.0
    prey.alive = False
    prey.remember_social("killed_by", animal.animal_id)
    carcass = world.add_carcass(prey)

    pack_kill = animal.pack_state.setdefault("shared_kill", {})
    pack_kill.clear()
    pack_kill.update(
        {
            "food_id": carcass.get("id"),
            "position": (carcass.get("x"), carcass.get("y")),
            "originator": animal.animal_id,
            "fed_priorities": set(),
            "blocked": set(),
            "participants": {animal.animal_id: feed_priority},
            "wait_counters": {},
            "stale_steps": 0,
            "feed_log": [],
        }
    )

    animal.pack_state["kill_origin"] = animal.animal_id
    animal.memory = {"x": carcass.get("x"), "y": carcass.get("y")}
    consumed = _consume_carcass(animal, world, carcass.get("id"))
    if consumed > 0.0:
        pack_kill.setdefault("fed_priorities", set()).add(feed_priority)
        pack_kill.setdefault("feed_log", []).append({"animal": animal.animal_id, "priority": feed_priority})
        log(f"{animal.name} abat {prey.name} et commence a manger ({consumed:.1f}).")
        return True, "pack_hunt_success", False

    animal.hunger = max(0.0, animal.hunger - 10.0)
    log(f"{animal.name} abat {prey.name} et cree une carcasse partagee.")
    return True, "pack_hunt_success", True
