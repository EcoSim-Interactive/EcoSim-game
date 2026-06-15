"""Coordonne la chasse cooperative et le partage des carcasses chez les carnivores."""
from __future__ import annotations

import random
from typing import Any, Iterable, Optional, Set, Tuple

from domain.constants import (
    CARNIVORE_EAT_DISTANCE,
    HUNGER_CRITICAL_FEED_OVERRIDE,
    PACK_FEED_WAIT_LIMIT_STEPS,
    PACK_KILL_STALE_STEPS,
)

from ..animal import Animal

PACK_TARGET_STALE_STEPS = 45  # Delai max avant d'abandonner une cible de meute devenue obsolesce.


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
    return priorities


def _state_set(state: dict[str, Any], key: str) -> Set[Any]:
    stored = state.get(key)
    if isinstance(stored, set):
        return stored
    normalized = set(stored or [])
    state[key] = normalized
    return normalized


def _state_dict(state: dict[str, Any], key: str) -> dict[Any, Any]:
    stored = state.get(key)
    if isinstance(stored, dict):
        return stored
    normalized: dict[Any, Any] = {}
    state[key] = normalized
    return normalized


def _feed_priority_for(member: Animal) -> float:
    role = str(member.get_trait("role", "")).lower()
    raw_hunt_cfg = member.get_trait("hunt")
    hunt_cfg: dict[str, Any] = raw_hunt_cfg if isinstance(raw_hunt_cfg, dict) else {}
    return _priority_value(
        member.get_trait("feed_priority"),
        _priority_value(hunt_cfg.get("feed_priority"), 40.0 if role in {"leader", "alpha"} else 60.0),
    )


def _prey_matches_targets(creature: Animal, targets: Optional[Set[str]]) -> bool:
    species_key = str(creature.species_type).lower()
    normalized_targets = {target.lower() for target in targets or set()}
    if normalized_targets:
        return species_key in normalized_targets
    return creature.diet == "herbivore"


def _nearest_prey(
    animal: Animal,
    animals: Iterable[Animal],
    targets: Optional[Set[str]] = None,
    world: Any | None = None,
) -> Optional[Animal]:
    best: Optional[Animal] = None
    best_distance: Optional[float] = None
    for creature in animals:
        if creature is animal or not creature.alive:
            continue
        if not _prey_matches_targets(creature, targets):
            continue
        if world is not None and hasattr(world, "_line_blocked_by_water"):
            if world._line_blocked_by_water(
                int(round(animal.x)),
                int(round(animal.y)),
                int(round(creature.x)),
                int(round(creature.y)),
            ):
                continue
        distance = animal.distance_to({"x": creature.x, "y": creature.y})
        if best_distance is None or distance < best_distance:
            best = creature
            best_distance = distance
    return best


def _find_prey_by_id(animals: Iterable[Animal], prey_id: Any) -> Optional[Animal]:
    for creature in animals:
        if creature.animal_id == prey_id and creature.alive:
            return creature
    return None


def _alive_pack_members(animal: Animal, animals: Iterable[Animal]) -> list[Animal]:
    if not animal.pack_id:
        return [animal]
    members = [
        other
        for other in animals
        if other.alive and other.pack_id == animal.pack_id
    ]
    return members or [animal]


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
    animal.apply_calories(consumed)
    animal.memory = None
    return consumed


def _reposition_pack_member(animal: Animal, world, action: str) -> Tuple[bool, str, bool]:
    """Force un pas de decalage quand la trajectoire directe echoue."""
    if animal.random_move(world):
        return True, action, False
    return False, "", False


def _sync_shared_target(animal: Animal, prey: Animal) -> None:
    if not animal.pack_id:
        return
    animal.pack_state["shared_target"] = {
        "prey_id": prey.animal_id,
        "position": (prey.x, prey.y),
        "selector": animal.animal_id,
        "species": prey.species_type,
        "stale_steps": 0,
    }


def _resolve_pack_target(
    animal: Animal,
    animals: Iterable[Animal],
    targets: Optional[Set[str]],
    world,
) -> Optional[Animal]:
    shared_target = animal.pack_state.get("shared_target") if animal.pack_id else None
    if isinstance(shared_target, dict):
        prey = _find_prey_by_id(animals, shared_target.get("prey_id"))
        if prey is not None and _prey_matches_targets(prey, targets):
            shared_target["position"] = (prey.x, prey.y)
            shared_target["stale_steps"] = 0
            return prey
        stale_steps = int(shared_target.get("stale_steps", 0)) + 1
        if stale_steps > PACK_TARGET_STALE_STEPS:
            animal.pack_state.pop("shared_target", None)
        else:
            shared_target["stale_steps"] = stale_steps

    prey = _nearest_prey(animal, animals, targets, world)
    if prey is not None:
        _sync_shared_target(animal, prey)
    return prey


def _sync_pack_participants(pack_kill: dict[str, Any], pack_members: Iterable[Animal]) -> dict[int, float]:
    participants = _state_dict(pack_kill, "participants")
    active_ids: set[int] = set()
    for member in pack_members:
        if not member.alive:
            continue
        active_ids.add(member.animal_id)
        participants[member.animal_id] = _feed_priority_for(member)

    stale_ids = [member_id for member_id in participants if member_id not in active_ids]
    for member_id in stale_ids:
        participants.pop(member_id, None)

    blocked = _state_set(pack_kill, "blocked")
    blocked.intersection_update(active_ids)

    fed_animals = _state_set(pack_kill, "fed_animals")
    fed_animals.intersection_update(active_ids)

    wait_counters = _state_dict(pack_kill, "wait_counters")
    for member_id in list(wait_counters):
        if member_id not in active_ids:
            wait_counters.pop(member_id, None)

    fed_priorities = _state_set(pack_kill, "fed_priorities")
    fed_priorities.clear()
    for member_id in fed_animals:
        priority = participants.get(member_id)
        if priority is not None:
            fed_priorities.add(priority)

    return participants


def _pending_required_members(
    wait_priorities: Set[float],
    participants: dict[int, float],
    fed_animals: Set[int],
    blocked: Set[int],
    *,
    exclude_id: Optional[int] = None,
) -> list[int]:
    if not wait_priorities:
        return []
    return [
        member_id
        for member_id, priority in participants.items()
        if member_id != exclude_id
        and priority in wait_priorities
        and member_id not in fed_animals
        and member_id not in blocked
    ]


def _handle_shared_kill(
    animal: Animal,
    pack_members: Iterable[Animal],
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

    participants = _sync_pack_participants(pack_kill, pack_members)
    participants[animal.animal_id] = feed_priority

    blocked = _state_set(pack_kill, "blocked")
    fed_animals = _state_set(pack_kill, "fed_animals")
    wait_counters = _state_dict(pack_kill, "wait_counters")

    if animal.animal_id in blocked:
        return False, "", False

    if distance > guard_radius and world is not None and hasattr(world, "_line_blocked_by_water"):
        if world._line_blocked_by_water(
            int(round(animal.x)),
            int(round(animal.y)),
            int(round(target_point["x"])),
            int(round(target_point["y"])),
        ):
            if animal.random_move(world):
                return True, "pack_reposition_for_carcass", False
            blocked.add(animal.animal_id)
            if participants and blocked.issuperset(participants.keys()):
                pack_kill.clear()
            return False, "", False

    if participants and blocked.issuperset(participants.keys()):
        pack_kill.clear()
        return False, "", False

    force_feed = animal.hunger >= HUNGER_CRITICAL_FEED_OVERRIDE
    pending_required = _pending_required_members(
        wait_priorities,
        participants,
        fed_animals,
        blocked,
        exclude_id=animal.animal_id,
    )

    def _line_blocked_from(origin: tuple[float, float]) -> bool:
        if world is None or not hasattr(world, "_line_blocked_by_water"):
            return False
        return world._line_blocked_by_water(
            int(round(origin[0])),
            int(round(origin[1])),
            int(round(target_point["x"])),
            int(round(target_point["y"])),
        )

    if pending_required and not force_feed:
        wait_count = int(wait_counters.get(animal.animal_id, 0)) + 1
        wait_counters[animal.animal_id] = wait_count
        if wait_count <= PACK_FEED_WAIT_LIMIT_STEPS:
            if distance > approach_radius:
                previous = (animal.x, animal.y)
                if animal.move_towards(target_point, world):
                    return True, "pack_waiting_move", False
                if animal.random_move(world):
                    return True, "pack_reposition_for_carcass", False
                if _line_blocked_from(previous):
                    blocked.add(animal.animal_id)
                    return False, "", False
            return True, "pack_waiting_guard", False
        force_feed = True

    if force_feed:
        wait_counters[animal.animal_id] = 0

    if animal.animal_id in fed_animals and not force_feed:
        if distance > guard_radius:
            previous = (animal.x, animal.y)
            if animal.move_towards(target_point, world):
                return True, "pack_guard_loop", False
            if animal.random_move(world):
                return True, "pack_reposition_guard", False
            if _line_blocked_from(previous):
                blocked.add(animal.animal_id)
                return False, "", False
        return True, "pack_guard_stand", False

    if distance > CARNIVORE_EAT_DISTANCE:
        previous = (animal.x, animal.y)
        if animal.move_towards(target_point, world):
            return True, "pack_move_to_carcass", False
        if animal.random_move(world):
            return True, "pack_reposition_for_carcass", False
        if _line_blocked_from(previous):
            blocked.add(animal.animal_id)
            return False, "", False

    fed_animals.add(animal.animal_id)
    _state_set(pack_kill, "fed_priorities").add(feed_priority)
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
    """Pilote la sequence complete de chasse, kill partage et ordre de nourrissage."""
    if animal.diet != "carnivore":
        return False, "", False

    animals = list(animals)
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

    pack_members = _alive_pack_members(animal, animals)
    if animal.pack_id and pack_bonus > 0:
        nearby = 0
        for other in pack_members:
            if other is animal:
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
            pack_members,
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

    prey = _resolve_pack_target(animal, animals, target_set, world)
    if not prey:
        return False, "", False

    prey_point = {"x": prey.x, "y": prey.y}
    distance_to_prey = animal.distance_to(prey_point)

    if distance_to_prey > chase_range:
        if animal.move_towards(prey_point, world):
            return True, "pack_tracking_prey", False
        return _reposition_pack_member(animal, world, "pack_reposition_for_prey")

    if distance_to_prey > attack_range:
        if animal.move_towards(prey_point, world):
            return True, "pack_closing_distance", False
        return _reposition_pack_member(animal, world, "pack_reposition_for_prey")

    if random.random() > success_rate:
        if not animal.move_towards(prey_point, world):
            moved, action, resolve = _reposition_pack_member(animal, world, "pack_reposition_after_attack_fail")
            if moved:
                _sync_shared_target(animal, prey)
                log(f"{animal.name} rate son attaque sur {prey.name}.")
                return True, action, resolve
        _sync_shared_target(animal, prey)
        log(f"{animal.name} rate son attaque sur {prey.name}.")
        return True, "pack_attack_failed", False

    prey.vitality = 0.0
    prey.alive = False
    prey.remember_social("killed_by", animal.animal_id)
    carcass = world.add_carcass(prey)

    animal.pack_state.pop("shared_target", None)
    pack_kill = animal.pack_state.setdefault("shared_kill", {})
    pack_kill.clear()
    pack_kill.update(
        {
            "food_id": carcass.get("id"),
            "position": (carcass.get("x"), carcass.get("y")),
            "originator": animal.animal_id,
            "fed_animals": set(),
            "fed_priorities": set(),
            "blocked": set(),
            "participants": {},
            "wait_counters": {},
            "stale_steps": 0,
            "feed_log": [],
        }
    )
    _sync_pack_participants(pack_kill, pack_members)

    animal.memory = {"x": carcass.get("x"), "y": carcass.get("y")}
    consumed = _consume_carcass(animal, world, carcass.get("id"))
    if consumed > 0.0:
        _state_set(pack_kill, "fed_animals").add(animal.animal_id)
        _state_set(pack_kill, "fed_priorities").add(feed_priority)
        pack_kill.setdefault("feed_log", []).append({"animal": animal.animal_id, "priority": feed_priority})
        log(f"{animal.name} abat {prey.name} et commence a manger ({consumed:.1f}).")
        return True, "pack_hunt_success", False

    log(f"{animal.name} abat {prey.name} et cree une carcasse partagee.")
    return True, "pack_hunt_success", True
