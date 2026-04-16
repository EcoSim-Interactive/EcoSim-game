"""Construit les snapshots de contexte utilises a chaque pas de simulation."""
from __future__ import annotations

import copy
from typing import Any, Dict, List


def compute_world_time(world: Any, step_index: int) -> Dict[str, int | bool]:
    """Calcule l'heure logique du monde pour le pas courant."""
    total_minutes = step_index * world.minutes_per_step
    hour = (total_minutes // 60) % 24
    minute = total_minutes % 60
    is_day = 6 <= hour < 20
    return {
        "hour": int(hour),
        "minute": int(minute),
        "is_day": is_day,
        "minutes_per_step": world.minutes_per_step,
    }


def build_step_frame(step_index: int, world_time: Dict[str, Any]) -> Dict[str, Any]:
    """Initialise la structure standard de donnees pour un tour de simulation."""
    return {
        "step": step_index + 1,
        "hour": int(world_time["hour"]),
        "minute": int(world_time["minute"]),
        "is_day": world_time["is_day"],
        "time_label": "jour" if world_time["is_day"] else "nuit",
        "species": [],
        "new_food_sources": [],
        "updated_food_sources": [],
        "removed_food_ids": [],
    }


def initialize_species_status(species: Any) -> Dict[str, Any]:
    """Capture the state of a species before applying the behaviour rules."""
    display_name = species.get_display_name() if hasattr(species, "get_display_name") else species.name
    original_name = getattr(species, "original_name", species.name)
    age_years = getattr(species, "age_years", None)
    age_stage = getattr(species, "age_stage", None)
    sex = getattr(species, "sex", None)
    return {
        "name": display_name,
        "display_name": display_name,
        "original_name": original_name,
        "sex": sex,
        "age_stage": age_stage,
        "age_years": age_years,
        "animal_id": getattr(species, "animal_id", None),
        "species_type": getattr(species, "species_type", getattr(species, "name", "")),
        "diet": getattr(species, "diet", None),
        "group_id": getattr(species, "group_id", None),
        "pack_id": getattr(species, "pack_id", None),
        "temperament": getattr(species, "temperament", None),
        "traits": copy.deepcopy(getattr(species, "traits", {})),
        "before": {
            "x": species.x,
            "y": species.y,
            "vitality": species.vitality,
            "consumed": species.consumed,
            "calories": getattr(species, "calories", None),
            "max_calories": getattr(species, "max_calories", None),
            "daily_calorie_need": getattr(species, "daily_calorie_need", None),
            "hunger": species.hunger,
            "thirst": species.thirst,
            "fatigue": species.fatigue,
            "resting": species.resting,
            "age_years": age_years,
            "age_stage": age_stage,
        },
        "action": "",
        "motivation": "",
        "after": {},
        "food_event": None,
    }


def finalize_species_status(species: Any, status: Dict[str, Any]) -> Dict[str, Any]:
    """Inject the updated state of the species once the behaviour has been resolved."""
    status.setdefault("food_event", None)
    status["after"] = {
        "x": species.x,
        "y": species.y,
        "vitality": species.vitality,
        "consumed": species.consumed,
        "calories": getattr(species, "calories", None),
        "max_calories": getattr(species, "max_calories", None),
        "daily_calorie_need": getattr(species, "daily_calorie_need", None),
        "hunger": species.hunger,
        "thirst": species.thirst,
        "fatigue": species.fatigue,
        "resting": species.resting,
        "alive": getattr(species, "alive", species.vitality > 0),
        "age_years": getattr(species, "age_years", None),
        "age_stage": getattr(species, "age_stage", None),
        "display_name": species.get_display_name() if hasattr(species, "get_display_name") else species.name,
    }
    status["age_years"] = status["after"].get("age_years")
    status["age_stage"] = status["after"].get("age_stage")
    status["display_name"] = status["after"].get("display_name", status.get("display_name"))
    status["name"] = status["display_name"] or status["name"]
    status["motivation"] = status.get("motivation", "")
    return status


def build_summary_payload(species_list: List[Any], world: Any) -> Dict[str, Any]:
    """Return an aggregate snapshot of the world after the simulation run."""
    return {
        "species": [
            {
                "name": s.name,
                "animal_id": getattr(s, "animal_id", None),
                "species_type": getattr(s, "species_type", getattr(s, "name", "")),
                "diet": getattr(s, "diet", None),
                "group_id": getattr(s, "group_id", None),
                "pack_id": getattr(s, "pack_id", None),
                "sex": getattr(s, "sex", None),
                "age_stage": getattr(s, "age_stage", None),
                "age_years": getattr(s, "age_years", None),
                "original_name": getattr(s, "original_name", getattr(s, "name", "")),
                "display_name": s.get_display_name() if hasattr(s, "get_display_name") else getattr(s, "name", ""),
                "traits": copy.deepcopy(getattr(s, "traits", {})),
                "position": [s.x, s.y],
                "vitality": s.vitality,
                "consumed": s.consumed,
                "calories": getattr(s, "calories", None),
                "max_calories": getattr(s, "max_calories", None),
                "daily_calorie_need": getattr(s, "daily_calorie_need", None),
                "hunger": s.hunger,
                "thirst": s.thirst,
                "fatigue": s.fatigue,
                "resting": s.resting,
            }
            for s in species_list
        ],
        "remaining_food": sum(
            1
            for food in world.food_sources
            if not hasattr(world, "food_has_supply") or world.food_has_supply(food)
        ),
        "remaining_water": sum(
            1
            for water in world.water_sources
            if not hasattr(world, "water_has_supply") or world.water_has_supply(water)
        ),
    }
