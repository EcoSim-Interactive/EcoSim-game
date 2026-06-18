"""Outils de generation procedurale des ressources alimentaires."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_FOOD_TYPE = "berries"
DEFAULT_FOOD_PROFILES: Dict[str, Dict[str, Any]] = {
    "berries": {
        "nutrition_range": [10000.0, 14000.0],
        "weight": 5,
        "metadata": {"category": "bush"},
    },
    "herbs": {
        "nutrition_range": [25000.0, 31000.0],
        "weight": 3,
        "metadata": {"category": "ground"},
    },
    "fruit_tree": {
        "nutrition_range": [38000.0, 46000.0],
        "weight": 2,
        "metadata": {"category": "tree"},
    },
}


def generate_food_sources(
    width: int,
    height: int,
    quantity: int = 0,
    *,
    distribution: Optional[Dict[str, int]] = None,
    type_weights: Optional[Dict[str, float]] = None,
    profiles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return a list of food source specifications with vegetal types."""
    profiles = profiles or DEFAULT_FOOD_PROFILES
    specs: List[Dict[str, Any]] = []

    if distribution:
        for raw_type, count in distribution.items():
            count_int = int(count) if isinstance(count, (int, float)) else 0
            if count_int <= 0:
                continue
            food_type, profile = resolve_food_profile(raw_type, profiles)
            for _ in range(count_int):
                specs.append(
                    _build_random_food_spec(width, height, food_type, profile)
                )
        return specs

    qty = int(quantity) if quantity else 0
    if qty <= 0:
        return specs

    types, weights = _prepare_weighted_types(profiles, type_weights)
    for _ in range(qty):
        food_type = random.choices(types, weights=weights, k=1)[0]
        _, profile = resolve_food_profile(food_type, profiles)
        specs.append(
            _build_random_food_spec(width, height, food_type, profile)
        )
    return specs


def resolve_food_profile(
    food_type: Optional[str],
    profiles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    profiles = profiles or DEFAULT_FOOD_PROFILES
    normalized = _normalize_type(food_type)
    if normalized in profiles:
        return normalized, profiles[normalized]
    default_profile = profiles[DEFAULT_FOOD_TYPE]
    return DEFAULT_FOOD_TYPE, default_profile


def _build_random_food_spec(
    width: int,
    height: int,
    food_type: str,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    x = random.randint(0, width)
    y = random.randint(0, height)
    metadata = profile.get("metadata")

    nutrition_range = profile.get("nutrition_range")
    if (
        isinstance(nutrition_range, (list, tuple))
        and len(nutrition_range) >= 2
    ):
        nutrition_value = random.uniform(
            nutrition_range[0], nutrition_range[1]
        )
    else:
        nutrition_value = float(profile.get("nutrition", 28000.0))

    return {
        "type": food_type,
        "food_class": "plant",
        "x": float(x),
        "y": float(y),
        "nutrition": float(nutrition_value),
        "metadata": dict(metadata) if isinstance(metadata, dict) else None,
    }


def _prepare_weighted_types(
    profiles: Dict[str, Dict[str, Any]],
    overrides: Optional[Dict[str, float]],
) -> Tuple[List[str], List[float]]:
    if overrides:
        types: List[str] = []
        weights: List[float] = []
        for raw_type, raw_weight in overrides.items():
            weight = (
                float(raw_weight)
                if isinstance(raw_weight, (int, float))
                else 0.0
            )
            if weight <= 0:
                continue
            food_type, profile = resolve_food_profile(raw_type, profiles)
            types.append(food_type)
            weights.append(weight)
        if types:
            return types, weights

    types = list(profiles.keys())
    weights = [
        float(profile.get("weight", 1)) for profile in profiles.values()
    ]
    return types, weights


def _normalize_type(name: Optional[str]) -> str:
    if not name or not isinstance(name, str):
        return DEFAULT_FOOD_TYPE
    return name.strip().lower().replace(" ", "_")
