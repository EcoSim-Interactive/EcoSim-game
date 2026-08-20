"""Domain entities describing living species: their vital gauges,
movement algorithms, and feeding/drinking behaviors.
"""

from __future__ import annotations

import math
import random
from abc import ABC
from typing import Any, Dict, Optional, Tuple

from .constants import (
    BASE_MINUTES_PER_STEP,
    CARNIVORE_EAT_DISTANCE,
    DEFAULT_CALORIE_RESERVE_DAYS,
    DEFAULT_DAILY_CALORIE_NEED,
    DEFAULT_MEAL_CALORIES,
    DRINK_DISTANCE,
    DRINK_THIRST_REDUCTION,
    EAT_DISTANCE,
    FATIGUE_RATE_PER_UNIT,
    FATIGUE_SLOWDOWN_FACTOR,
    FATIGUE_SLOWDOWN_THRESHOLD,
    MINUTES_PER_RATE_UNIT,
    MOVE_FATIGUE_PER_UNIT,
    MOVE_TARGET_EPSILON,
    RANDOM_MOVE_ATTEMPTS,
    REST_CALORIE_BURN_FACTOR,
    REST_FATIGUE_RECOVERY_PER_UNIT,
    REST_VITALITY_RECOVERY_PER_UNIT,
    THIRST_RATE_PER_UNIT,
    VITALITY_FATIGUE_PENALTY_PER_UNIT,
    VITALITY_FATIGUE_THRESHOLD,
    VITALITY_HUNGER_PENALTY_PER_UNIT,
    VITALITY_HUNGER_THRESHOLD,
    VITALITY_RECOVERY_FATIGUE_MAX,
    VITALITY_RECOVERY_HUNGER_MAX,
    VITALITY_RECOVERY_RATE_PER_UNIT,
    VITALITY_RECOVERY_THIRST_MAX,
    VITALITY_THIRST_PENALTY_PER_UNIT,
    VITALITY_THIRST_THRESHOLD,
)


class Species(ABC):
    """Abstract domain entity representing a living creature in the simulation.

    Defines core physical capabilities, vital status tracking, spatial
    movement algorithms, and resource consumption methods.

    Attributes:
        name (str): Identifier or species name.
        sprite_name (str): Visual asset identifier for rendering.
        x (float): Horizontal position coordinate.
        y (float): Vertical position coordinate.
        vision (float): Sensory vision range radius.
        smell_range (float): Olfactory perception range radius.
        speed (float): Maximum movement speed per step.
        diurnal (bool): True if active during daytime, False if nocturnal.
        temperament (str): Behavioral trait (e.g., 'neutre', 'agressif').
        diet (str): Dietary classification ('herbivore', 'carnivore', etc.).
        vitality (float): Current health/vitality score (0 to 100).
        calories (float): Current energetic reserve in kcal.
        hunger (float): Hunger gauge percentage derived from calorie deficit.
        thirst (float): Thirst level percentage (0 to 100).
        fatigue (float): Exhaustion level percentage (0 to 100).
        resting (bool): Indicates if entity is currently sleeping/resting.
        alive (bool): Living status flag.
    """

    def __init__(
        self,
        name: str,
        position: Tuple[float, float],
        vision: float = 100,
        smell_range: float = 50,
        speed: float = 5,
        diurnal: bool = True,
        temperament: str = "neutre",
        diet: str = "omnivore",
        body_nutrition: Optional[float] = None,
        age_years: float = 0.0,
        daily_calorie_need: float = DEFAULT_DAILY_CALORIE_NEED,
        calorie_reserve_days: float = DEFAULT_CALORIE_RESERVE_DAYS,
        meal_calories: float = DEFAULT_MEAL_CALORIES,
        body_mass_kg: Optional[float] = None,
        sprite_name: Optional[str] = None,
        carcass_edible_ratio: float = 0.55,
        carcass_calories_per_kg: float = 1800.0,
    ) -> None:
        """Initialize the species with its physical and energetic
        parameters.

        Most public attributes are documented on the class
        docstring; this also derives calorie/body-mass bookkeeping
        (max_calories, body_nutrition, etc.) used by the hunger
        gauge and carcass calculations.
        """
        self.name = name
        self.sprite_name = sprite_name or name.lower()
        self.x, self.y = position
        self.vision = vision
        self.smell_range = smell_range
        self.speed = speed
        self.diurnal = diurnal
        self.temperament = temperament
        self.diet = diet
        self.age_years = float(age_years)
        self.daily_calorie_need = max(1.0, float(daily_calorie_need))
        self.calorie_reserve_days = max(0.25, float(calorie_reserve_days))
        self.max_calories = self.daily_calorie_need * self.calorie_reserve_days
        self.calories = self.max_calories
        self.meal_calories = max(1.0, float(meal_calories))
        self.base_body_mass_kg = Species._coerce_positive_float(body_mass_kg)
        self.body_mass_kg = self.base_body_mass_kg
        self.carcass_edible_ratio = self._normalize_ratio(
            carcass_edible_ratio, fallback=0.55
        )
        self.carcass_calories_per_kg = max(1.0, float(carcass_calories_per_kg))
        self.body_nutrition = self._resolve_body_nutrition(body_nutrition)

        self.vitality = 100.0
        self.consumed = 0
        self.memory: Optional[Dict[str, float]] = None
        self.rest_steps = 0  # compteur pour les siestes
        self.max_rest_steps = 3  # limite pour les repos volontaires

        # Besoins vitaux
        self.hunger = 0.0
        self.thirst = 0.0
        self.fatigue = 0.0
        self.resting = False
        self.alive = True

    @staticmethod
    def _coerce_positive_float(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0.0 else None

    @staticmethod
    def _normalize_ratio(value: Any, *, fallback: float) -> float:
        try:
            ratio = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(0.05, min(1.0, ratio))

    def estimate_carcass_calories(self) -> float:
        """Estime les calories effectivement disponibles dans la carcasse."""
        if self.body_mass_kg is None:
            return 0.0
        return max(
            0.0,
            self.body_mass_kg
            * self.carcass_edible_ratio
            * self.carcass_calories_per_kg,
        )

    def _resolve_body_nutrition(
        self, explicit_value: Optional[float]
    ) -> float:
        explicit = Species._coerce_positive_float(explicit_value)
        if explicit is not None:
            return explicit
        estimated = self.estimate_carcass_calories()
        if estimated > 0.0:
            return estimated
        return 80.0

    @property
    def hunger(self) -> float:
        """Expose une jauge de faim derivee du deficit calorique courant."""
        if self.max_calories <= 0.0:
            return 100.0
        deficit = max(0.0, self.max_calories - self.calories)
        return max(0.0, min(100.0, (deficit / self.max_calories) * 100.0))

    @hunger.setter
    def hunger(self, value: float) -> None:
        """Sets hunger gauge percentage by updating internal calorie count.

        Args:
            value (float): Target hunger percentage (0 to 100).
        """
        try:
            hunger_percent = float(value)
        except (TypeError, ValueError):
            hunger_percent = 0.0
        hunger_percent = max(0.0, min(100.0, hunger_percent))
        self.calories = self.max_calories * (1.0 - (hunger_percent / 100.0))

    def calorie_deficit(self) -> float:
        """Computes current missing calories required to reach max capacity.

        Returns:
            float: Calorie deficit in kcal.
        """
        return max(0.0, self.max_calories - self.calories)

    def apply_calories(self, value: float) -> float:
        """Adds calories to reserve and returns amount actually absorbed.

        Args:
            value (float): Amount of calories to add.

        Returns:
            float: Net calories added to reserve.
        """
        try:
            delta = float(value)
        except (TypeError, ValueError):
            return 0.0
        if delta <= 0.0:
            return 0.0
        previous = self.calories
        self.calories = min(self.max_calories, self.calories + delta)
        return self.calories - previous

    def burn_calories(self, value: float) -> float:
        """Consumes calories from reserve and returns amount actually spent.

        Args:
            value (float): Amount of calories to burn.

        Returns:
            float: Net calories deducted from reserve.
        """
        try:
            delta = float(value)
        except (TypeError, ValueError):
            return 0.0
        if delta <= 0.0:
            return 0.0
        previous = self.calories
        self.calories = max(0.0, self.calories - delta)
        return previous - self.calories

    def distance_to(self, target: Dict[str, float]) -> float:
        """Computes the Euclidean distance to a target position.

        Args:
            target (Dict[str, float]): Position with "x" and "y".

        Returns:
            float: Distance in world units.
        """
        return math.sqrt(
            (self.x - target["x"]) ** 2 + (self.y - target["y"]) ** 2
        )

    def _distance_to_water(self, world: Any, water: Dict[str, float]) -> float:
        if hasattr(world, "distance_to_water"):
            return world.distance_to_water(self.x, self.y, water)
        return self.distance_to(water)

    def move_towards(
        self, target: Dict[str, float], world: Any = None
    ) -> bool:
        """Steps the entity towards a target position, dodging obstacles.

        Effective speed is reduced when fatigued and scaled to the
        world's step duration. If the world blocks the straight
        path (e.g. water too deep to cross), tries a fan of steering
        angles around the direct heading and moves to the reachable
        point closest to the target instead. The move is clamped to
        world bounds and increases fatigue in proportion to the
        distance actually travelled.

        Args:
            target (Dict[str, float]): Position with "x" and "y".
            world (Any): World used for obstacle/bounds checks, or
                None to move unconditionally.

        Returns:
            bool: True if the entity moved, False otherwise.
        """
        if self.resting:
            return False

        dx = target["x"] - self.x
        dy = target["y"] - self.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist < MOVE_TARGET_EPSILON:
            return False

        # La fatigue reduit la vitesse effective pour eviter des deplacements
        # irreels.
        fatigue_factor = (
            FATIGUE_SLOWDOWN_FACTOR
            if self.fatigue > FATIGUE_SLOWDOWN_THRESHOLD
            else 1.0
        )
        scale = 1.0
        if world is not None and hasattr(world, "minutes_per_step"):
            try:
                scale = float(world.minutes_per_step) / BASE_MINUTES_PER_STEP
            except (TypeError, ValueError):
                scale = 1.0
            if scale <= 0:
                scale = 1.0
        effective_speed = self.speed * fatigue_factor * scale
        move_dist = min(dist, effective_speed)

        new_x = self.x + move_dist * dx / dist
        new_y = self.y + move_dist * dy / dist

        if world is not None and hasattr(world, "can_entity_enter"):
            if not world.can_entity_enter(self, new_x, new_y):
                # Try sliding/steering around the obstacle.
                moved = False
                angle_offsets = (
                    0.0,
                    30.0,
                    -30.0,
                    60.0,
                    -60.0,
                    90.0,
                    -90.0,
                    120.0,
                    -120.0,
                    150.0,
                    -150.0,
                    180.0,
                )
                base_angle = math.atan2(dy, dx)
                best = None
                best_dist = None
                for offset in angle_offsets:
                    angle = base_angle + math.radians(offset)
                    alt_x = self.x + math.cos(angle) * move_dist
                    alt_y = self.y + math.sin(angle) * move_dist
                    if hasattr(world, "width") and hasattr(world, "height"):
                        alt_x = max(0.0, min(float(world.width), alt_x))
                        alt_y = max(0.0, min(float(world.height), alt_y))
                    if not world.can_entity_enter(self, alt_x, alt_y):
                        continue
                    dist_to_target = (target["x"] - alt_x) ** 2 + (
                        target["y"] - alt_y
                    ) ** 2
                    if best is None or dist_to_target < best_dist:
                        best = (alt_x, alt_y)
                        best_dist = dist_to_target
                if best is not None:
                    new_x, new_y = best
                    moved = True
                if not moved:
                    return False

        if (
            world is not None
            and hasattr(world, "width")
            and hasattr(world, "height")
        ):
            new_x = max(0.0, min(float(world.width), new_x))
            new_y = max(0.0, min(float(world.height), new_y))

        travelled = math.sqrt((new_x - self.x) ** 2 + (new_y - self.y) ** 2)
        if travelled < MOVE_TARGET_EPSILON:
            return False

        self.x = new_x
        self.y = new_y

        # Le cout de deplacement depend directement de la distance parcourue.
        self.fatigue += MOVE_FATIGUE_PER_UNIT * travelled
        return True

    def random_move(self, world: Any) -> bool:
        """Moves the entity one step in a random direction.

        Tries up to RANDOM_MOVE_ATTEMPTS random headings at the
        fatigue-adjusted effective speed until one lands on a tile
        the entity can enter, applying the resulting fatigue cost.

        Args:
            world (Any): World used for obstacle/bounds checks.

        Returns:
            bool: True if a valid random move was made, False if
                every attempt was blocked.
        """
        if self.resting:
            return False

        fatigue_factor = (
            FATIGUE_SLOWDOWN_FACTOR
            if self.fatigue > FATIGUE_SLOWDOWN_THRESHOLD
            else 1.0
        )
        scale = 1.0
        if hasattr(world, "minutes_per_step"):
            try:
                scale = float(world.minutes_per_step) / BASE_MINUTES_PER_STEP
            except (TypeError, ValueError):
                scale = 1.0
            if scale <= 0:
                scale = 1.0
        effective_speed = self.speed * fatigue_factor * scale

        for _ in range(RANDOM_MOVE_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)

            new_x = max(0.0, min(world.width, self.x + dx * effective_speed))
            new_y = max(0.0, min(world.height, self.y + dy * effective_speed))

            if hasattr(
                world, "can_entity_enter"
            ) and not world.can_entity_enter(self, new_x, new_y):
                continue

            move_dist = math.sqrt(
                (new_x - self.x) ** 2 + (new_y - self.y) ** 2
            )
            self.x, self.y = new_x, new_y
            self.fatigue += MOVE_FATIGUE_PER_UNIT * move_dist
            return True
        return False

    def try_eat(self, world: Any) -> Optional[Dict[str, Any]]:
        """Attempts to eat from a nearby matching food source.

        Scans the world's food sources for one that still has
        supply, matches the entity's diet, and lies within eating
        distance (extended for carnivores eating meat/carrion), then
        consumes as much as needed to cover the calorie deficit.

        Args:
            world (Any): World providing food sources and
                consumption helpers.

        Returns:
            Optional[Dict[str, Any]]: Consumption payload if food
                was eaten, otherwise None.
        """
        for food in list(world.food_sources):
            if hasattr(world, "food_has_supply") and not world.food_has_supply(
                food
            ):
                continue
            if hasattr(
                world, "food_matches_diet"
            ) and not world.food_matches_diet(food, self.diet):
                continue
            distance_threshold = EAT_DISTANCE
            if (
                self.diet == "carnivore"
                and food.get("food_class") in {"meat", "carrion"}
                and CARNIVORE_EAT_DISTANCE > distance_threshold
            ):
                distance_threshold = CARNIVORE_EAT_DISTANCE
            if self.distance_to(food) <= distance_threshold:
                required = self._compute_required_food_amount(food)
                result = (
                    world.consume_food(food, required)
                    if hasattr(world, "consume_food")
                    else None
                )
                if result and result.get("consumed", 0.0) > 0.0:
                    self.consumed += 1
                    consumed = float(result["consumed"])
                    self.apply_calories(consumed)
                    self.memory = None
                    payload = result.get("food") or {}
                    payload["consumed"] = consumed
                    payload["removed"] = result.get("removed", False)
                    payload["food_id"] = payload.get("id")
                    return payload
        return None

    def try_drink(self, world: Any) -> bool:
        """Attempts to drink from a nearby water source.

        First checks the water tiles immediately adjacent to the
        entity's position (shore drinking), then falls back to any
        water source within DRINK_DISTANCE. On success, reduces
        thirst, remembers the water location, and updates any shared
        group/pack memory of the last known water.

        Args:
            world (Any): World providing water sources and
                consumption helpers.

        Returns:
            bool: True if water was consumed, False otherwise.
        """

        def _consume_from(water_source: Dict[str, Any]) -> bool:
            if hasattr(
                world, "water_has_supply"
            ) and not world.water_has_supply(water_source):
                return False
            if not hasattr(world, "consume_water") or world.consume_water(
                water_source
            ):
                self.thirst = max(0.0, self.thirst - DRINK_THIRST_REDUCTION)
                if hasattr(self, "remember_water"):
                    try:
                        self.remember_water(
                            water_source.get("x", 0.0),
                            water_source.get("y", 0.0),
                        )
                    except Exception:
                        pass
                group_state = getattr(self, "group_state", None)
                if isinstance(group_state, dict):
                    group_state["last_water"] = {
                        "x": water_source.get("x", 0.0),
                        "y": water_source.get("y", 0.0),
                    }
                pack_state = getattr(self, "pack_state", None)
                if isinstance(pack_state, dict):
                    pack_state["last_water"] = {
                        "x": water_source.get("x", 0.0),
                        "y": water_source.get("y", 0.0),
                    }
                return True
            return False

        # Autorise la consommation si l'animal se trouve au bord
        # d'une zone d'eau.
        if hasattr(world, "_water_tiles") and hasattr(
            world, "_water_tile_lookup"
        ):
            cx = int(round(self.x))
            cy = int(round(self.y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    key = (cx + dx, cy + dy)
                    if key in world._water_tiles:
                        water = world._water_tile_lookup.get(key)
                        if water and _consume_from(water):
                            return True

        for water in world.water_sources:
            if self._distance_to_water(world, water) < DRINK_DISTANCE:
                if _consume_from(water):
                    return True
        return False

    def smell_for_food(self, world: Any) -> Optional[Dict[str, float]]:
        """Detects a matching food source by smell beyond vision range.

        Args:
            world (Any): World providing food sources.

        Returns:
            Optional[Dict[str, float]]: Nearest matching food source
                strictly beyond vision but within smell_range, or
                None.
        """
        for food in world.food_sources:
            if hasattr(world, "food_has_supply") and not world.food_has_supply(
                food
            ):
                continue
            if hasattr(
                world, "food_matches_diet"
            ) and not world.food_matches_diet(food, self.diet):
                continue
            distance = self.distance_to(food)
            if self.vision < distance <= self.smell_range:
                return food
        return None

    def smell_for_water(self, world: Any) -> Optional[Dict[str, float]]:
        """Detects a water source by smell beyond vision range.

        Args:
            world (Any): World providing water sources.

        Returns:
            Optional[Dict[str, float]]: Nearest water source
                strictly beyond vision but within smell_range, or
                None.
        """
        for water in world.water_sources:
            if hasattr(
                world, "water_has_supply"
            ) and not world.water_has_supply(water):
                continue
            distance = self._distance_to_water(world, water)
            if self.vision < distance <= self.smell_range:
                return water
        return None

    def _compute_required_food_amount(self, food: Dict[str, Any]) -> float:
        remaining = float(
            food.get("remaining_nutrition", food.get("nutrition", 0.0))
        )
        deficit = self.calorie_deficit()
        if deficit <= 0.0:
            return 0.0
        return min(remaining, deficit, self.meal_calories)

    def update_vitals(self, world_time: Dict[str, float]) -> None:
        """Advances hunger, thirst, fatigue, and vitality by one step.

        Burns calories according to the daily need (reduced while
        resting), raises thirst and fatigue over time, applies
        vitality penalties once hunger/thirst/fatigue cross their
        thresholds (recording a death cause when vitality reaches
        zero), grants passive vitality recovery when all needs are
        low, and lets resting accelerate fatigue/vitality recovery.
        Finally clamps every gauge to its valid range and updates
        the alive flag.

        Args:
            world_time (Dict[str, float]): Time context with
                "minutes_per_step".
        """
        minutes = world_time["minutes_per_step"]
        rate_scale = minutes / MINUTES_PER_RATE_UNIT

        # La faim est maintenant derivee d'une reserve calorique reelle.
        daily_burn = self.daily_calorie_need * (minutes / (24.0 * 60.0))
        rest_factor = REST_CALORIE_BURN_FACTOR if self.resting else 1.0
        self.burn_calories(daily_burn * rest_factor)
        self.thirst += THIRST_RATE_PER_UNIT * rate_scale

        # La fatigue continue de monter hors phase de repos.
        if not self.resting:
            self.fatigue += FATIGUE_RATE_PER_UNIT * rate_scale

        # Les besoins critiques entament directement la vitalite.
        if self.hunger > VITALITY_HUNGER_THRESHOLD:
            self.vitality -= VITALITY_HUNGER_PENALTY_PER_UNIT * rate_scale
            if self.vitality <= 0 and not getattr(self, "death_cause", None):
                self.death_cause = "Mort de faim"
        if self.thirst > VITALITY_THIRST_THRESHOLD:
            self.vitality -= VITALITY_THIRST_PENALTY_PER_UNIT * rate_scale
            if self.vitality <= 0 and not getattr(self, "death_cause", None):
                self.death_cause = "Mort de soif"
        if self.fatigue > VITALITY_FATIGUE_THRESHOLD:
            self.vitality -= VITALITY_FATIGUE_PENALTY_PER_UNIT * rate_scale
            if self.vitality <= 0 and not getattr(self, "death_cause", None):
                self.death_cause = "Épuisement"

        # Un individu en bon etat recupere progressivement de la vitalite.
        if (
            self.hunger < VITALITY_RECOVERY_HUNGER_MAX
            and self.thirst < VITALITY_RECOVERY_THIRST_MAX
            and self.fatigue < VITALITY_RECOVERY_FATIGUE_MAX
        ):
            self.vitality += VITALITY_RECOVERY_RATE_PER_UNIT * rate_scale

        # Le repos accelere la recuperation et ralentit l'usure.
        if self.resting:
            self.fatigue = max(
                0.0, self.fatigue - REST_FATIGUE_RECOVERY_PER_UNIT * rate_scale
            )
            self.vitality += REST_VITALITY_RECOVERY_PER_UNIT * rate_scale

        # Bornage final pour conserver des valeurs metier coherentes.
        self.vitality = max(0.0, min(100.0, self.vitality))
        self.calories = max(0.0, min(self.max_calories, self.calories))
        self.thirst = min(100.0, self.thirst)
        self.fatigue = min(100.0, self.fatigue)
        self.alive = self.vitality > 0.0
