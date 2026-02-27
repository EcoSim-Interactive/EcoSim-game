"""Domain entity representing a species inside the world."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional, Tuple

from .constants import (
    BASE_MINUTES_PER_STEP,
    CARNIVORE_EAT_DISTANCE,
    DRINK_DISTANCE,
    DRINK_THIRST_REDUCTION,
    EAT_DISTANCE,
    FATIGUE_SLOWDOWN_FACTOR,
    FATIGUE_SLOWDOWN_THRESHOLD,
    HUNGER_BASELINE,
    HUNGER_RATE_PER_UNIT,
    MINUTES_PER_RATE_UNIT,
    MOVE_FATIGUE_PER_UNIT,
    MOVE_TARGET_EPSILON,
    RANDOM_MOVE_ATTEMPTS,
    REST_FATIGUE_RECOVERY_PER_UNIT,
    REST_VITALITY_RECOVERY_PER_UNIT,
    THIRST_RATE_PER_UNIT,
    FATIGUE_RATE_PER_UNIT,
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


class Species:
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
        body_nutrition: float = 80.0,
        age_years: float = 0.0,
    ) -> None:
        self.name = name
        self.x, self.y = position
        self.vision = vision
        self.smell_range = smell_range
        self.speed = speed
        self.diurnal = diurnal
        self.temperament = temperament
        self.diet = diet
        self.body_nutrition = body_nutrition
        self.age_years = float(age_years)

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

    def distance_to(self, target: Dict[str, float]) -> float:
        return math.sqrt((self.x - target["x"]) ** 2 + (self.y - target["y"]) ** 2)

    def _distance_to_water(self, world: Any, water: Dict[str, float]) -> float:
        if hasattr(world, "distance_to_water"):
            return world.distance_to_water(self.x, self.y, water)
        return self.distance_to(water)


    def move_towards(self, target: Dict[str, float], world: Any = None) -> None:
        if self.resting:
            return

        dx = target["x"] - self.x
        dy = target["y"] - self.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist < MOVE_TARGET_EPSILON:
            return

        # Reduction de vitesse si fatigue elevee
        fatigue_factor = FATIGUE_SLOWDOWN_FACTOR if self.fatigue > FATIGUE_SLOWDOWN_THRESHOLD else 1.0
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
                angle_offsets = (0.0, 30.0, -30.0, 60.0, -60.0, 90.0, -90.0, 120.0, -120.0, 150.0, -150.0, 180.0)
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
                    dist_to_target = (target["x"] - alt_x) ** 2 + (target["y"] - alt_y) ** 2
                    if best is None or dist_to_target < best_dist:
                        best = (alt_x, alt_y)
                        best_dist = dist_to_target
                if best is not None:
                    new_x, new_y = best
                    moved = True
                if not moved:
                    return

        if world is not None and hasattr(world, "width") and hasattr(world, "height"):
            new_x = max(0.0, min(float(world.width), new_x))
            new_y = max(0.0, min(float(world.height), new_y))

        self.x = new_x
        self.y = new_y

        # Consommation basee sur la distance
        self.fatigue += MOVE_FATIGUE_PER_UNIT * move_dist

    def random_move(self, world: Any) -> None:
        if self.resting:
            return

        fatigue_factor = FATIGUE_SLOWDOWN_FACTOR if self.fatigue > FATIGUE_SLOWDOWN_THRESHOLD else 1.0
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

            if hasattr(world, "can_entity_enter") and not world.can_entity_enter(self, new_x, new_y):
                continue

            move_dist = math.sqrt((new_x - self.x) ** 2 + (new_y - self.y) ** 2)
            self.x, self.y = new_x, new_y
            self.fatigue += MOVE_FATIGUE_PER_UNIT * move_dist
            return

    def try_eat(self, world: Any) -> Optional[Dict[str, Any]]:
        for food in list(world.food_sources):
            if hasattr(world, "food_has_supply") and not world.food_has_supply(food):
                continue
            if hasattr(world, "food_matches_diet") and not world.food_matches_diet(food, self.diet):
                continue
            distance_threshold = EAT_DISTANCE
            if self.diet == "carnivore" and food.get("food_class") in {"meat", "carrion"} and CARNIVORE_EAT_DISTANCE > distance_threshold:
                distance_threshold = CARNIVORE_EAT_DISTANCE
            if self.distance_to(food) < distance_threshold:
                required = self._compute_required_food_amount(food)
                result = world.consume_food(food, required) if hasattr(world, "consume_food") else None
                if result and result.get("consumed", 0.0) > 0.0:
                    self.consumed += 1
                    consumed = float(result["consumed"])
                    self.hunger = max(0.0, self.hunger - consumed)
                    self.memory = None
                    payload = result.get("food") or {}
                    payload["consumed"] = consumed
                    payload["removed"] = result.get("removed", False)
                    payload["food_id"] = payload.get("id")
                    return payload
        return None

    def try_drink(self, world: Any) -> bool:
        def _consume_from(water_source: Dict[str, Any]) -> bool:
            if hasattr(world, "water_has_supply") and not world.water_has_supply(water_source):
                return False
            if not hasattr(world, "consume_water") or world.consume_water(water_source):
                self.thirst = max(0.0, self.thirst - DRINK_THIRST_REDUCTION)
                if hasattr(self, "remember_water"):
                    try:
                        self.remember_water(water_source.get("x", 0.0), water_source.get("y", 0.0))
                    except Exception:
                        pass
                group_state = getattr(self, "group_state", None)
                if isinstance(group_state, dict):
                    group_state["last_water"] = {"x": water_source.get("x", 0.0), "y": water_source.get("y", 0.0)}
                pack_state = getattr(self, "pack_state", None)
                if isinstance(pack_state, dict):
                    pack_state["last_water"] = {"x": water_source.get("x", 0.0), "y": water_source.get("y", 0.0)}
                return True
            return False

        # Shoreline drinking: if standing next to water tile, allow drinking.
        if hasattr(world, "_water_tiles") and hasattr(world, "_water_tile_lookup"):
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
        for food in world.food_sources:
            if hasattr(world, "food_has_supply") and not world.food_has_supply(food):
                continue
            if hasattr(world, "food_matches_diet") and not world.food_matches_diet(food, self.diet):
                continue
            distance = self.distance_to(food)
            if self.vision < distance <= self.smell_range:
                return food
        return None

    def smell_for_water(self, world: Any) -> Optional[Dict[str, float]]:
        for water in world.water_sources:
            if hasattr(world, "water_has_supply") and not world.water_has_supply(water):
                continue
            distance = self._distance_to_water(world, water)
            if self.vision < distance <= self.smell_range:
                return water
        return None

    def _compute_required_food_amount(self, food: Dict[str, Any]) -> float:
        remaining = float(food.get("remaining_nutrition", food.get("nutrition", 0.0)))
        hunger_factor = max(self.hunger, 0.0)
        baseline = HUNGER_BASELINE if hunger_factor <= 0.0 else hunger_factor
        return min(remaining, baseline)

    def update_vitals(self, world_time: Dict[str, float]) -> None:
        minutes = world_time["minutes_per_step"]
        rate_scale = minutes / MINUTES_PER_RATE_UNIT

        # Metabolisme
        self.hunger += HUNGER_RATE_PER_UNIT * rate_scale
        self.thirst += THIRST_RATE_PER_UNIT * rate_scale

        # Fatigue augmente naturellement si on ne se repose pas
        if not self.resting:
            self.fatigue += FATIGUE_RATE_PER_UNIT * rate_scale

        # Penalite vitale si besoins critiques
        if self.hunger > VITALITY_HUNGER_THRESHOLD:
            self.vitality -= VITALITY_HUNGER_PENALTY_PER_UNIT * rate_scale
        if self.thirst > VITALITY_THIRST_THRESHOLD:
            self.vitality -= VITALITY_THIRST_PENALTY_PER_UNIT * rate_scale
        if self.fatigue > VITALITY_FATIGUE_THRESHOLD:
            self.vitality -= VITALITY_FATIGUE_PENALTY_PER_UNIT * rate_scale

        # Regeneration si tous les indicateurs sont bas
        if self.hunger < VITALITY_RECOVERY_HUNGER_MAX and self.thirst < VITALITY_RECOVERY_THIRST_MAX and self.fatigue < VITALITY_RECOVERY_FATIGUE_MAX:
            self.vitality += VITALITY_RECOVERY_RATE_PER_UNIT * rate_scale

        # Recuperation plus rapide si repos
        if self.resting:
            self.fatigue = max(0.0, self.fatigue - REST_FATIGUE_RECOVERY_PER_UNIT * rate_scale)
            self.vitality += REST_VITALITY_RECOVERY_PER_UNIT * rate_scale

        # Clamp final
        self.vitality = max(0.0, min(100.0, self.vitality))
        self.hunger = min(100.0, self.hunger)
        self.thirst = min(100.0, self.thirst)
        self.fatigue = min(100.0, self.fatigue)
        self.alive = self.vitality > 0.0
