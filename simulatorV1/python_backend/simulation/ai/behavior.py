"""Routines comportementales elementaires separees du modele de donnees."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from domain.constants import (
    DRINK_TARGET_SEARCH_RADIUS,
    WATER_MEMORY_SEARCH_RADIUS,
)

if TYPE_CHECKING:
    from ..animal import Animal

LogFn = Callable[[str], None]

# Nombre d'echecs consecutifs de move_towards vers l'eau avant de forcer une
# recherche de rive garantie en visibilite directe (voir _move_to_water_target)
WATER_SEEK_FAILURE_ESCAPE_LIMIT = 3


def _reposition_after_failed_move(
    animal: "Animal",
    world: Any,
    log: LogFn,
    *,
    action: str,
    motivation: str,
) -> Tuple[bool, str, str]:
    """Tente un decalage court lorsque la cible directe est inaccessible."""
    if animal.random_move(world):
        msg = (
            f"{animal.name} tente un repositionnement pour "
            f"contourner un blocage."
        )
        log(msg)
        return True, action, motivation
    return False, "", ""


def _resolve_water_source(
    world: Any, x: float, y: float
) -> Optional[Dict[str, Any]]:
    """Retrieves a water source from a remembered or observed position.

    Args:
        world (Any): World simulation state.
        x (float): Horizontal position coordinate.
        y (float): Vertical position coordinate.

    Returns:
        Optional[Dict[str, Any]]: Water source entity or None.
    """
    if not hasattr(world, "get_nearest_water"):
        return None
    return world.get_nearest_water(x, y)


def _remember_water_access(
    animal: "Animal", water: Dict[str, Any], target: Tuple[float, float]
) -> None:
    animal.remember_water(
        float(water.get("x", animal.x)), float(water.get("y", animal.y))
    )
    animal.remember_water_target(target[0], target[1])


def _move_to_water_target(
    animal: "Animal",
    world: Any,
    log: LogFn,
    *,
    target: Tuple[float, float],
    action: str,
    motivation: str,
) -> Tuple[bool, str, str]:
    """Poursuit une cible de rive stable pour eviter les
    oscillations de bord d'eau.
    """
    if animal.distance_to({"x": target[0], "y": target[1]}) <= 1.0:
        animal.clear_water_target()
        return False, "", ""
    if not animal.move_towards({"x": target[0], "y": target[1]}, world):
        animal.clear_water_target()
        streak = animal.note_water_seek_failure()
        if streak >= WATER_SEEK_FAILURE_ESCAPE_LIMIT and hasattr(
            world, "find_shore_tile"
        ):
            # move_towards() ne fait que de la ligne droite avec un leger
            # eventail d'angles de repli sur une seule distance de pas : un
            # animal coince dans une anse/presqu'ile entouree d'eau trop
            # profonde peut echouer indefiniment sans jamais se rapprocher.
            # find_shore_tile() cherche depuis la position REELLE actuelle
            # et ne retient que des tuiles de rive dont la ligne de vue ne
            # traverse aucune eau, donc forcement atteignables en ligne
            # directe.
            shore = world.find_shore_tile(
                animal.x, animal.y, DRINK_TARGET_SEARCH_RADIUS
            )
            if shore is not None and animal.move_towards(
                {"x": shore[0], "y": shore[1]}, world
            ):
                animal.remember_water_target(shore[0], shore[1])
                animal.reset_water_seek_failures()
                log(
                    f"{animal.name} contourne un obstacle pour "
                    "rejoindre une rive accessible."
                )
                if animal.try_drink(world):
                    animal.clear_water_target()
                    log(f"{animal.name} a bu !")
                    return True, "drink", motivation
                return True, action, motivation
        return _reposition_after_failed_move(
            animal,
            world,
            log,
            action="reposition_for_water",
            motivation=f"{motivation} -> acces bloque",
        )
    animal.reset_water_seek_failures()
    if animal.try_drink(world):
        animal.clear_water_target()
        log(f"{animal.name} a bu !")
        return True, "drink", motivation
    return True, action, motivation


def decide_idle_action(animal: "Animal") -> str:
    """Choisit entre repos et errance lorsqu'aucune urgence n'est detectee."""
    if animal.rest_steps >= animal.max_rest_steps:
        animal.rest_steps = 0
        return "wander"

    roll = __import__("random").random()
    if animal.temperament == "agite":
        return "rest" if roll < 0.2 else "wander"
    if animal.temperament == "prudent":
        return "rest" if roll < 0.8 else "wander"
    return "rest" if roll < 0.5 else "wander"


def handle_thirst(
    animal: "Animal", world: Any, log: LogFn
) -> Tuple[bool, str, str]:
    """Drives an animal towards water and drinks when possible.

    Tries, in order: drinking immediately if already at the shore;
    continuing towards a remembered water target; moving towards
    water seen or smelled nearby; and finally falling back to a
    group/pack-shared water memory, personal memory, or the nearest
    known source on the map.

    Args:
        animal (Animal): Thirsty animal deciding its action.
        world (Any): World providing water sources and helpers.
        log (LogFn): Callback used to record a human-readable
            narration of the chosen action.

    Returns:
        Tuple[bool, str, str]: (acted, action, motivation).
    """
    if animal.try_drink(world):
        animal.clear_water_target()
        log(f"{animal.name} a bu des qu'il a atteint la rive.")
        return True, "drink", "soif (rive atteinte)"

    remembered_target = animal.recall_water_target()
    if remembered_target is not None:
        water = animal.recall_water()
        if water is not None:
            source = _resolve_water_source(world, water[0], water[1])
            if source is not None:
                log(f"{animal.name} poursuit une rive memorisee pour boire.")
                acted, action, motivation = _move_to_water_target(
                    animal,
                    world,
                    log,
                    target=remembered_target,
                    action="move_to_known_water",
                    motivation="soif (cible memorisee)",
                )
                if acted:
                    return acted, action, motivation
        animal.clear_water_target()

    nearest = _resolve_water_source(world, animal.x, animal.y)
    if nearest is not None and hasattr(world, "distance_to_water"):
        water_distance = float(
            world.distance_to_water(animal.x, animal.y, nearest)
        )
        if water_distance <= animal.vision:
            target = (
                world.find_drink_target(
                    animal.x, animal.y, nearest, entity=animal
                )
                if hasattr(world, "find_drink_target")
                else (
                    float(nearest.get("x", animal.x)),
                    float(nearest.get("y", animal.y)),
                )
            )
            log(f"{animal.name} voit une source d'eau a proximite")
            _remember_water_access(animal, nearest, target)
            return _move_to_water_target(
                animal,
                world,
                log,
                target=target,
                action="move_to_water",
                motivation="soif (vue)",
            )
        if water_distance <= animal.smell_range:
            target = (
                world.find_drink_target(
                    animal.x, animal.y, nearest, entity=animal
                )
                if hasattr(world, "find_drink_target")
                else (
                    float(nearest.get("x", animal.x)),
                    float(nearest.get("y", animal.y)),
                )
            )
            log(f"{animal.name} sent de l'eau a proximite")
            _remember_water_access(animal, nearest, target)
            return _move_to_water_target(
                animal,
                world,
                log,
                target=target,
                action="move_to_water",
                motivation="soif (odorat)",
            )

    memory_point: Optional[Tuple[float, float]] = None
    source = ""
    shared = None
    if isinstance(animal.group_state, dict):
        shared = animal.group_state.get("last_water")
    if shared is None and isinstance(animal.pack_state, dict):
        shared = animal.pack_state.get("last_water")
    if isinstance(shared, dict) and "x" in shared and "y" in shared:
        memory_point = (
            float(shared.get("x", animal.x)),
            float(shared.get("y", animal.y)),
        )
        source = "groupe"
    else:
        recalled = animal.recall_water()
        if recalled is not None:
            memory_point = recalled
            source = "memoire"
    if memory_point is None and hasattr(world, "get_nearest_water"):
        nearest = world.get_nearest_water(animal.x, animal.y)
        if nearest is not None:
            memory_point = (
                float(nearest.get("x", animal.x)),
                float(nearest.get("y", animal.y)),
            )
            source = "repere"

    if memory_point is not None:
        water = _resolve_water_source(world, memory_point[0], memory_point[1])
        if water is None:
            return False, "", ""
        if hasattr(world, "find_drink_target"):
            shore = world.find_drink_target(
                animal.x,
                animal.y,
                water,
                entity=animal,
                search_radius=WATER_MEMORY_SEARCH_RADIUS,
            )
        else:
            shore = (
                float(water.get("x", animal.x)),
                float(water.get("y", animal.y)),
            )
        log(f"{animal.name} se dirige vers un point d'eau (source {source}).")
        _remember_water_access(animal, water, shore)
        return _move_to_water_target(
            animal,
            world,
            log,
            target=shore,
            action="move_to_known_water",
            motivation=f"soif ({source})",
        )

    return False, "", ""


def handle_fatigue(animal: "Animal", log: LogFn) -> Tuple[bool, str, str]:
    """Forces an exhausted animal to rest for this step.

    Args:
        animal (Animal): Animal that must rest.
        log (LogFn): Callback used to record the action.

    Returns:
        Tuple[bool, str, str]: (acted, action, motivation), always
            (True, "resting", ...).
    """
    animal.resting = True
    animal.rest_steps += 1
    log(f"{animal.name} se repose.")
    return True, "resting", "repos du a la fatigue"


def handle_cycle_rest(animal: "Animal", log: LogFn) -> Tuple[bool, str, str]:
    """Puts an animal to rest per its day/night activity cycle.

    Args:
        animal (Animal): Animal resting due to its diurnal/nocturnal
            cycle.
        log (LogFn): Callback used to record the action.

    Returns:
        Tuple[bool, str, str]: (acted, action, motivation), always
            (True, "resting_cycle", ...).
    """
    animal.resting = True
    animal.rest_steps += 1
    log(f"{animal.name} dort selon son rythme naturel.")
    return True, "resting_cycle", "repos impose par le cycle jour/nuit"


def handle_hunger(
    animal: "Animal", world: Any, log: LogFn
) -> Tuple[bool, str, str]:
    """Drives a hungry animal towards food it can perceive or recall.

    Tries, in order: food currently in sight, food detected by
    smell, and a remembered food location, moving towards whichever
    is found first and resetting the memory/rest counters
    accordingly.

    Args:
        animal (Animal): Hungry animal deciding its action.
        world (Any): World providing food sources and helpers.
        log (LogFn): Callback used to record the chosen action.

    Returns:
        Tuple[bool, str, str]: (acted, action, motivation), or
            (False, "", "") if no food lead is available.
    """
    food = (
        world.get_nearest_food(
            animal.x, animal.y, diet=animal.diet, entity=animal
        )
        if hasattr(world, "get_nearest_food")
        else None
    )
    if food and animal.distance_to(food) <= animal.vision:
        log(f"{animal.name} voit de la nourriture a {food}")
        animal.memory = food
        if not animal.move_towards(food, world):
            animal.memory = None
            return _reposition_after_failed_move(
                animal,
                world,
                log,
                action="reposition_for_food",
                motivation="faim (vue) -> acces bloque",
            )
        animal.rest_steps = 0
        return True, "move_to_seen_food", "faim (vue)"

    scented = animal.smell_for_food(world)
    if scented is not None:
        log(f"{animal.name} sent de la nourriture a {scented}")
        animal.memory = scented
        if not animal.move_towards(scented, world):
            animal.memory = None
            return _reposition_after_failed_move(
                animal,
                world,
                log,
                action="reposition_for_food",
                motivation="faim (odorat) -> acces bloque",
            )
        animal.rest_steps = 0
        return True, "move_to_smelt_food", "faim (odorat)"

    if animal.memory:
        log(f"{animal.name} se souvient d'une nourriture a {animal.memory}")
        if not animal.move_towards(animal.memory, world):
            animal.memory = None
            return _reposition_after_failed_move(
                animal,
                world,
                log,
                action="reposition_for_food",
                motivation="faim (memoire) -> acces bloque",
            )
        animal.rest_steps = 0
        return True, "move_to_memory", "faim (memoire)"

    return False, "", ""


def handle_idle(animal: "Animal", world: Any, log: LogFn) -> Tuple[str, str]:
    """Chooses an idle-time action when no urgent need was detected.

    Delegates to decide_idle_action() for a rest-vs-wander choice
    influenced by temperament, falling back to reporting a blocked
    wander when random_move() cannot find a free tile.

    Args:
        animal (Animal): Animal with no pending urgent need.
        world (Any): World used for movement checks.
        log (LogFn): Callback used to record the chosen action.

    Returns:
        Tuple[str, str]: (action, motivation).
    """
    choice = decide_idle_action(animal)
    if choice == "rest":
        animal.resting = True
        animal.rest_steps += 1
        log(f"{animal.name} ne percoit rien. Il decide de se reposer.")
        return (
            "resting_idle",
            f"repos influence par temperament '{animal.temperament}'",
        )

    if animal.random_move(world):
        log(f"{animal.name} ne percoit rien. Il erre par reflexe.")
        return (
            "wander",
            f"errance influencee par temperament '{animal.temperament}'",
        )
    log(f"{animal.name} ne percoit rien mais reste bloque sur place.")
    return "idle_blocked", "errance impossible a cause d'un blocage spatial"
