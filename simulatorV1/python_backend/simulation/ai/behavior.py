"""Animal decision-making logic separated from data models."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple, TYPE_CHECKING

from domain.constants import WATER_MEMORY_SEARCH_RADIUS

if TYPE_CHECKING:
    from ..animal import Animal

LogFn = Callable[[str], None]


def decide_idle_action(animal: "Animal") -> str:
    """Decide whether the animal should rest or wander when idle."""
    if animal.rest_steps >= animal.max_rest_steps:
        animal.rest_steps = 0
        return "wander"

    roll = __import__("random").random()
    if animal.temperament == "agite":
        return "rest" if roll < 0.2 else "wander"
    if animal.temperament == "prudent":
        return "rest" if roll < 0.8 else "wander"
    return "rest" if roll < 0.5 else "wander"


def handle_thirst(animal: "Animal", world: Any, log: LogFn) -> Tuple[bool, str, str]:
    shore = None
    if hasattr(world, "find_shore_tile"):
        shore = world.find_shore_tile(animal.x, animal.y, animal.vision)
    if shore is not None:
        log(f"{animal.name} voit une source d'eau a proximite")
        animal.remember_water(shore[0], shore[1])
        animal.move_towards({"x": shore[0], "y": shore[1]}, world)
        if animal.try_drink(world):
            log(f"{animal.name} a bu !")
            return True, "drink", "soif (vue)"
        return True, "move_to_water", "soif (vue)"

    if hasattr(world, "find_shore_tile"):
        shore = world.find_shore_tile(animal.x, animal.y, animal.smell_range, min_radius=animal.vision + 1)
    if shore is not None:
        log(f"{animal.name} sent de l'eau a proximite")
        animal.remember_water(shore[0], shore[1])
        animal.move_towards({"x": shore[0], "y": shore[1]}, world)
        if animal.try_drink(world):
            log(f"{animal.name} a bu apres l'avoir sentie !")
            return True, "drink", "soif (odorat)"
        return True, "move_to_water", "soif (odorat)"

    memory_point: Optional[Tuple[float, float]] = None
    source = ""
    shared = None
    if isinstance(animal.group_state, dict):
        shared = animal.group_state.get("last_water")
    if shared is None and isinstance(animal.pack_state, dict):
        shared = animal.pack_state.get("last_water")
    if isinstance(shared, dict) and "x" in shared and "y" in shared:
        memory_point = (float(shared.get("x", animal.x)), float(shared.get("y", animal.y)))
        source = "groupe"
    else:
        recalled = animal.recall_water()
        if recalled is not None:
            memory_point = recalled
            source = "memoire"
    if memory_point is None and hasattr(world, "get_nearest_water"):
        nearest = world.get_nearest_water(animal.x, animal.y)
        if nearest is not None:
            memory_point = (float(nearest.get("x", animal.x)), float(nearest.get("y", animal.y)))
            source = "repere"

    if memory_point is not None:
        if hasattr(world, "find_shore_tile"):
            shore = world.find_shore_tile(memory_point[0], memory_point[1], WATER_MEMORY_SEARCH_RADIUS)
        else:
            shore = None
        if shore is None:
            shore = memory_point
        log(f"{animal.name} se dirige vers un point d'eau (source {source}).")
        animal.move_towards({"x": shore[0], "y": shore[1]}, world)
        if animal.try_drink(world):
            log(f"{animal.name} a bu !")
            return True, "drink", f"soif ({source})"
        return True, "move_to_known_water", f"soif ({source})"

    return False, "", ""


def handle_fatigue(animal: "Animal", log: LogFn) -> Tuple[bool, str, str]:
    animal.resting = True
    animal.rest_steps += 1
    log(f"{animal.name} se repose.")
    return True, "resting", "repos du a la fatigue"


def handle_cycle_rest(animal: "Animal", log: LogFn) -> Tuple[bool, str, str]:
    animal.resting = True
    animal.rest_steps += 1
    log(f"{animal.name} dort selon son rythme naturel.")
    return True, "resting_cycle", "repos impose par le cycle jour/nuit"


def handle_hunger(animal: "Animal", world: Any, log: LogFn) -> Tuple[bool, str, str]:
    food = world.get_nearest_food(animal.x, animal.y)
    if food and animal.distance_to(food) <= animal.vision:
        log(f"{animal.name} voit de la nourriture a {food}")
        animal.memory = food
        animal.move_towards(food, world)
        animal.rest_steps = 0
        return True, "move_to_seen_food", "faim (vue)"

    scented = animal.smell_for_food(world)
    if scented is not None:
        log(f"{animal.name} sent de la nourriture a {scented}")
        animal.memory = scented
        animal.move_towards(scented, world)
        animal.rest_steps = 0
        return True, "move_to_smelt_food", "faim (odorat)"

    if animal.memory:
        log(f"{animal.name} se souvient d'une nourriture a {animal.memory}")
        animal.move_towards(animal.memory, world)
        animal.rest_steps = 0
        return True, "move_to_memory", "faim (memoire)"

    return False, "", ""


def handle_idle(animal: "Animal", world: Any, log: LogFn) -> Tuple[str, str]:
    choice = decide_idle_action(animal)
    if choice == "rest":
        animal.resting = True
        animal.rest_steps += 1
        log(f"{animal.name} ne percoit rien. Il decide de se reposer.")
        return "resting_idle", f"repos influence par temperament '{animal.temperament}'"

    animal.random_move(world)
    log(f"{animal.name} ne percoit rien. Il erre par reflexe.")
    return "wander", f"errance influencee par temperament '{animal.temperament}'"
