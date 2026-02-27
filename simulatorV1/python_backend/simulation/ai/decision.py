"""Decision tree for per-animal actions."""
from __future__ import annotations

from typing import Any, Dict, Optional

from domain.constants import (
    EXPLORE_HUNGER_THRESHOLD,
    EXPLORE_THIRST_THRESHOLD,
    FATIGUE_CRITICAL_THRESHOLD,
    FATIGUE_MODERATE_THRESHOLD,
    HUNGER_MODERATE_THRESHOLD,
    HUNGER_OVERRIDES_THIRST_THRESHOLD,
    THIRST_BLOCKS_REST_THRESHOLD,
    THIRST_CRITICAL_THRESHOLD,
    THIRST_MODERATE_THRESHOLD,
)

from ..action_executor import resolve_consumption
from ..ai.relationships import handle_species_relationships


def process_species(
    animal,
    status: Dict[str, Any],
    world_time: Dict[str, Any],
    world,
    species_list,
    logger,
) -> Optional[Dict[str, Any]]:
    """Apply the decision tree and update status in-place."""
    thirst = animal.thirst
    hunger = animal.hunger
    fatigue = animal.fatigue
    animal.resting = False
    food_result: Optional[Dict[str, Any]] = None

    def record(action: str, motivation: str, *, resolve_food: bool = False) -> None:
        nonlocal food_result
        status["action"] = action
        status["motivation"] = motivation
        if resolve_food:
            result = resolve_consumption(world, animal, logger.log)
            if result["action_suffix"]:
                status["action"] += result["action_suffix"]
            event = result.get("food_event")
            if event:
                status["food_event"] = event
            food_result = result

    # Priority 1: critical thirst (always overrides rest)
    if thirst > THIRST_CRITICAL_THRESHOLD:
        acted, action, motivation = animal.handle_thirst(world, logger.log)
        if acted:
            record(action, motivation)
            return food_result
        # If we cannot see/smell water, keep moving to find it.
        animal.random_move(world)
        record("seek_water", "soif critique -> exploration", resolve_food=True)
        return food_result

    # Priority 2: critical fatigue (unless thirst is already pressing)
    if fatigue > FATIGUE_CRITICAL_THRESHOLD and thirst < THIRST_BLOCKS_REST_THRESHOLD:
        acted, action, motivation = animal.handle_fatigue(logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priority 3: forced rest due to day/night cycle (skip if thirsty)
    is_day = world_time["is_day"]
    if (animal.diurnal and not is_day) or (not animal.diurnal and is_day):
        if thirst < THIRST_BLOCKS_REST_THRESHOLD:
            acted, action, motivation = animal.handle_cycle_rest(logger.log)
            if acted:
                record(action, motivation)
                return food_result

    # Let very hungry carnivores hunt even if moderately thirsty.
    if animal.diet == "carnivore" and hunger > HUNGER_OVERRIDES_THIRST_THRESHOLD:
        related, action, motivation, resolve = handle_species_relationships(
            animal,
            species_list,
            world,
            logger.log,
        )
        if related:
            record(action, motivation, resolve_food=resolve)
            return food_result

    # Priority 4: moderate thirst
    if thirst > THIRST_MODERATE_THRESHOLD:
        acted, action, motivation = animal.handle_thirst(world, logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priority 5: moderate fatigue (skip if thirst is high)
    if fatigue > FATIGUE_MODERATE_THRESHOLD and thirst < THIRST_BLOCKS_REST_THRESHOLD:
        acted, action, motivation = animal.handle_fatigue(logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priority 6: social relations and species-specific behaviours
    related, action, motivation, resolve = handle_species_relationships(
        animal,
        species_list,
        world,
        logger.log,
    )
    if related:
        record(action, motivation, resolve_food=resolve)
        return food_result

    # Priority 7: hunger
    if hunger > HUNGER_MODERATE_THRESHOLD:
        acted, action, motivation = animal.handle_hunger(world, logger.log)
        if acted:
            record(action, motivation, resolve_food=True)
            return food_result

    # Priority 8: explore when mildly hungry or thirsty
    if hunger > EXPLORE_HUNGER_THRESHOLD or thirst > EXPLORE_THIRST_THRESHOLD:
        animal.random_move(world)
        record("explore_for_food_or_water", "faim/soif mais rien detecte -> exploration", resolve_food=True)
        return food_result

    # Priority 9: idle behaviour based on temperament
    action, motivation = animal.handle_idle(world, logger.log)
    record(action, motivation, resolve_food=True)
    return food_result
