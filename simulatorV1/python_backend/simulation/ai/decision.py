"""Arbre de decision principal applique a chaque individu a chaque tour."""

from __future__ import annotations

from typing import Any, Dict, Optional

from domain.constants import (
    EXPLORE_HUNGER_THRESHOLD,
    EXPLORE_THIRST_THRESHOLD,
    FATIGUE_CRITICAL_THRESHOLD,
    FATIGUE_MODERATE_THRESHOLD,
    HUNGER_CRITICAL_FEED_OVERRIDE,
    HUNGER_MODERATE_THRESHOLD,
    HUNGER_OVERRIDES_THIRST_THRESHOLD,
    THIRST_BLOCKS_REST_THRESHOLD,
    THIRST_CRITICAL_THRESHOLD,
    THIRST_MODERATE_THRESHOLD,
)

from ..action_executor import resolve_consumption
from ..ai.relationships import handle_species_relationships


def _has_active_feeding_opportunity(animal) -> bool:
    """Detecte une opportunite alimentaire sociale qui justifie
    d'interrompre le repos.
    """
    pack_state = getattr(animal, "pack_state", None)
    if isinstance(pack_state, dict):
        shared_kill = pack_state.get("shared_kill")
        if isinstance(shared_kill, dict) and shared_kill.get("food_id"):
            return True

    scavenger_cfg = animal.get_trait("scavenger")
    if isinstance(scavenger_cfg, dict):
        followed = scavenger_cfg.get("follow_packs")
        if isinstance(followed, (list, tuple, set)):
            for pack_id in followed:
                state = (
                    animal.pack_state_for(str(pack_id))
                    if hasattr(animal, "pack_state_for")
                    else None
                )
                if isinstance(state, dict):
                    shared_kill = state.get("shared_kill")
                    if isinstance(shared_kill, dict) and shared_kill.get(
                        "food_id"
                    ):
                        return True
    return False


def _resolve_critical_hunger(
    animal, world, species_list, logger, record
) -> bool:
    """Force une recherche alimentaire active avant les besoins seulement moderes."""  # noqa: E501
    if animal.hunger < HUNGER_CRITICAL_FEED_OVERRIDE:
        return False

    if animal.diet == "carnivore":
        related, action, motivation, resolve = handle_species_relationships(
            animal,
            species_list,
            world,
            logger.log,
        )
        if related:
            record(action, motivation, resolve_food=resolve)
            return True

    acted, action, motivation = animal.handle_hunger(world, logger.log)
    if acted:
        record(action, motivation, resolve_food=True)
        return True

    if animal.random_move(world):
        record("seek_food", "faim critique -> exploration", resolve_food=True)
    else:
        record(
            "seek_food_blocked",
            "faim critique mais deplacement impossible",
            resolve_food=True,
        )
    return True


def process_species(
    animal,
    status: Dict[str, Any],
    world_time: Dict[str, Any],
    world,
    species_list,
    logger,
) -> Optional[Dict[str, Any]]:
    """Applique l'arbre de decision et met a jour l'etat serialise de l'animal."""  # noqa: E501
    thirst = animal.thirst
    hunger = animal.hunger
    fatigue = animal.fatigue
    animal.resting = False
    food_result: Optional[Dict[str, Any]] = None

    def record(
        action: str, motivation: str, *, resolve_food: bool = False
    ) -> None:
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

    # Priorite 1: la soif critique passe avant tout le reste.
    if thirst > THIRST_CRITICAL_THRESHOLD:
        acted, action, motivation = animal.handle_thirst(world, logger.log)
        if acted:
            record(action, motivation)
            return food_result
        # If we cannot see/smell water, keep moving to find it.
        if animal.random_move(world):
            record(
                "seek_water", "soif critique -> exploration", resolve_food=True
            )
        else:
            record(
                "seek_water_blocked",
                "soif critique mais deplacement impossible",
                resolve_food=True,
            )
        return food_result

    # Priorite 2: une opportunite alimentaire sociale ne doit pas etre perdue.
    if (
        _has_active_feeding_opportunity(animal)
        and thirst < THIRST_CRITICAL_THRESHOLD
    ):
        related, action, motivation, resolve = handle_species_relationships(
            animal,
            species_list,
            world,
            logger.log,
        )
        if related:
            record(action, motivation, resolve_food=resolve)
            return food_result

    # Priorite 3: une faim critique passe avant le repos impose et la soif seulement moderee.  # noqa: E501
    if thirst < THIRST_CRITICAL_THRESHOLD and _resolve_critical_hunger(
        animal,
        world,
        species_list,
        logger,
        record,
    ):
        return food_result

    # Priorite 4: la fatigue critique impose un repos, sauf urgence hydrique ou alimentaire.  # noqa: E501
    if (
        fatigue > FATIGUE_CRITICAL_THRESHOLD
        and thirst < THIRST_BLOCKS_REST_THRESHOLD
    ):
        acted, action, motivation = animal.handle_fatigue(logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priorite 5: respect du cycle jour/nuit si l'animal n'est pas en deficit hydrique.  # noqa: E501
    is_day = world_time["is_day"]
    if (animal.diurnal and not is_day) or (not animal.diurnal and is_day):
        if thirst < THIRST_BLOCKS_REST_THRESHOLD:
            acted, action, motivation = animal.handle_cycle_rest(logger.log)
            if acted:
                record(action, motivation)
                return food_result

    # Un carnivore tres affame peut chasser avant de traiter une soif moderee.
    if (
        animal.diet == "carnivore"
        and hunger > HUNGER_OVERRIDES_THIRST_THRESHOLD
    ):
        related, action, motivation, resolve = handle_species_relationships(
            animal,
            species_list,
            world,
            logger.log,
        )
        if related:
            record(action, motivation, resolve_food=resolve)
            return food_result

    # Priorite 6: soif moderee.
    if thirst > THIRST_MODERATE_THRESHOLD:
        acted, action, motivation = animal.handle_thirst(world, logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priorite 7: fatigue moderee, tant que la soif reste sous controle.
    if (
        fatigue > FATIGUE_MODERATE_THRESHOLD
        and thirst < THIRST_BLOCKS_REST_THRESHOLD
    ):
        acted, action, motivation = animal.handle_fatigue(logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priorite 8: comportements sociaux et logiques propres a l'espece.
    related, action, motivation, resolve = handle_species_relationships(
        animal,
        species_list,
        world,
        logger.log,
    )
    if related:
        record(action, motivation, resolve_food=resolve)
        return food_result

    # Priorite 9: gestion de la faim.
    if hunger > HUNGER_MODERATE_THRESHOLD:
        acted, action, motivation = animal.handle_hunger(world, logger.log)
        if acted:
            record(action, motivation, resolve_food=True)
            return food_result

    # Priorite 10: exploration si un besoin existe mais sans cible detectee.
    if hunger > EXPLORE_HUNGER_THRESHOLD or thirst > EXPLORE_THIRST_THRESHOLD:
        if animal.random_move(world):
            record(
                "explore_for_food_or_water",
                "faim/soif mais rien detecte -> exploration",
                resolve_food=True,
            )
        else:
            record(
                "explore_blocked",
                "faim/soif mais exploration impossible",
                resolve_food=True,
            )
        return food_result

    # Priorite 11: comportement neutre pilote par le temperament.
    action, motivation = animal.handle_idle(world, logger.log)
    record(action, motivation, resolve_food=True)
    return food_result
