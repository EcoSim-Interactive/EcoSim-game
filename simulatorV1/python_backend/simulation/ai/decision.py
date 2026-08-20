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
            fed_animals = shared_kill.get("fed_animals", set())
            if animal.animal_id in fed_animals:
                if (
                    animal.fatigue > FATIGUE_MODERATE_THRESHOLD
                    or animal.thirst > THIRST_BLOCKS_REST_THRESHOLD
                ):
                    return False
            else:
                if (
                    animal.fatigue > FATIGUE_CRITICAL_THRESHOLD
                    or animal.thirst > THIRST_CRITICAL_THRESHOLD
                ):
                    return False
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
                        fed_animals = shared_kill.get("fed_animals", set())
                        if animal.animal_id in fed_animals:
                            if (
                                animal.fatigue > FATIGUE_MODERATE_THRESHOLD
                                or animal.thirst > THIRST_BLOCKS_REST_THRESHOLD
                            ):
                                continue
                        else:
                            if (
                                animal.fatigue > FATIGUE_CRITICAL_THRESHOLD
                                or animal.thirst > THIRST_CRITICAL_THRESHOLD
                            ):
                                continue
                        return True
    return False


def _resolve_critical_hunger(
    animal, world, species_list, logger, record
) -> bool:
    """Forces active food search before moderate needs."""
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
    """Evaluates decision tree and updates serialized animal status.

    Args:
        animal (Animal): Target animal entity evaluating actions.
        status (Dict[str, Any]): Mutable status dictionary for serialization.
        world_time (Dict[str, Any]): Environment time context mapping.
        world: World environment instance.
        species_list: Active species list.
        logger: Event logger adapter.

    Returns:
        Optional[Dict[str, Any]]: Food resolution payload if food was eaten.
    """
    thirst = animal.thirst
    hunger = animal.hunger
    fatigue = animal.fatigue
    animal.resting = False
    food_result: Optional[Dict[str, Any]] = None

    def record(
        action: str, motivation: str, *, resolve_food: bool = False
    ) -> None:
        """Records the chosen action/motivation onto the status payload.

        Marks the animal as resting for pack-guard actions, and when
        resolve_food is set, resolves food consumption and merges
        its action suffix / food event into the status and the
        enclosing food_result.

        Args:
            action (str): Action identifier to store.
            motivation (str): Human-readable motivation string.
            resolve_food (bool): Whether to also resolve a food
                consumption for this action.
        """
        nonlocal food_result
        status["action"] = action
        status["motivation"] = motivation
        if action in {"pack_guard_stand", "pack_waiting_guard"}:
            animal.resting = True
        if resolve_food:
            result = resolve_consumption(world, animal, logger.log)
            if result["action_suffix"]:
                status["action"] += result["action_suffix"]
            event = result.get("food_event")
            if event:
                status["food_event"] = event
            food_result = result

    # Priorite 0: Fuite de panique sous attaque d'un predateur.
    under_attack = (
        animal.recall_social("under_attack")
        if hasattr(animal, "recall_social")
        else None
    )
    if under_attack:
        import math

        predator_x, predator_y = under_attack
        dx = animal.x - predator_x
        dy = animal.y - predator_y
        dist = math.sqrt(dx**2 + dy**2)
        animal.remember_social("under_attack", None)
        if dist > 0:
            target_point = {
                "x": animal.x + (dx / dist) * animal.speed * 1.5,
                "y": animal.y + (dy / dist) * animal.speed * 1.5,
            }
            if animal.move_towards(target_point, world):
                record(
                    "flee_predator",
                    "sous attaque de predateur -> fuite de panique",
                )
                return food_result

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

    # Priorite 2: fatigue critique impose un repos, meme en cas de faim.
    # Sans ce garde-fou, un individu dont la faim reste au-dessus du seuil
    # critique (HUNGER_CRITICAL_FEED_OVERRIDE) ne redescend jamais en-dessous
    # et la priorite 4 (faim critique, chasse/recherche en boucle) capture
    # systematiquement la decision avant que le repos ne soit jamais atteint
    # : la fatigue reste plafonnee a 100 jusqu'a la mort par epuisement.
    if (
        fatigue > FATIGUE_CRITICAL_THRESHOLD
        and thirst < THIRST_BLOCKS_REST_THRESHOLD
    ):
        acted, action, motivation = animal.handle_fatigue(logger.log)
        if acted:
            record(action, motivation)
            return food_result

    # Priorite 3: une opportunite alimentaire sociale ne doit pas etre perdue.
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

    # Priorite 4: faim critique avant repos et soif moderee.
    if thirst < THIRST_CRITICAL_THRESHOLD and _resolve_critical_hunger(
        animal,
        world,
        species_list,
        logger,
        record,
    ):
        return food_result

    # Priorite 5: respect du cycle jour/nuit.
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
