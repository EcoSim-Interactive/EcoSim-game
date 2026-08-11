"""Components encapsulating vital, aging, and metabolic logic."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional, Tuple


class AgeComponent:
    """Manages aging progression profiles and old-age survival.

    Attributes:
        age_years (float): Current age of the entity in years.
        age_units (str): Unit measurement tag (defaults to 'years').
        age_profile (list[Dict[str, Any]]): Normalized life stages.
        age_stage (str): Active stage label ('juvenile', 'adult').
    """

    def __init__(
        self,
        age_years: float,
        age_profile_spec: Any,
        default_units: str = "years",
    ) -> None:
        """Initializes AgeComponent with age state and configuration.

        Args:
            age_years (float): Initial age value.
            age_profile_spec (Any): Stage specification dictionary.
            default_units (str): Default time unit tag. Defaults to "years".
        """
        self.age_years = age_years
        self.age_units = default_units
        self.age_profile = self._normalize_age_profile(age_profile_spec)
        self.age_stage = self._compute_age_stage()

    def _normalize_age_profile(self, spec: Any) -> list[Dict[str, Any]]:
        """Normalizes and sorts raw age profile specifications into a list.

        Args:
            spec (Any): Raw age profile specification object.

        Returns:
            list[Dict[str, Any]]: Sorted stage configuration dictionaries.
        """
        stages: list[Dict[str, Any]] = []
        if isinstance(spec, dict):
            self.age_units = (
                spec.get("units", "years")
                if isinstance(spec.get("units"), str)
                else "years"
            )
            raw_entries = (
                spec.get("stages", [])
                if isinstance(spec.get("stages"), list)
                else []
            )
        elif isinstance(spec, list):
            raw_entries = spec
        else:
            return []

        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            name_value = entry.get("name") or entry.get("label")
            if not isinstance(name_value, str) or not name_value.strip():
                continue
            name = name_value.strip().lower()
            try:
                minimum = float(entry.get("min", 0.0))
            except (TypeError, ValueError):
                continue
            try:
                maximum = float(entry.get("max", float("inf")))
            except (TypeError, ValueError):
                maximum = float("inf")
            try:
                death_prob = float(entry.get("death_prob_per_year", 0.0))
            except (TypeError, ValueError):
                death_prob = 0.0

            stages.append(
                {
                    "name": name,
                    "min": max(0.0, minimum),
                    "max": max(0.0, maximum),
                    "death_prob": max(0.0, min(1.0, death_prob)),
                    "metabolism": entry.get("metabolism"),
                }
            )

        stages.sort(key=lambda s: float(s["min"]))
        return stages

    def _compute_age_stage(self) -> str:
        """Computes active age stage name based on current age_years.

        Returns:
            str: Stage name identifier (e.g., 'adult', 'juvenile').
        """
        if not self.age_profile:
            return "adult"
        for stage in self.age_profile:
            if stage["min"] <= self.age_years < stage["max"]:
                return str(stage["name"])
        if self.age_profile:
            return str(self.age_profile[-1]["name"])
        return "adult"

    def tick_age(
        self, delta_years: float
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Advances entity age and evaluates old-age mortality risk.

        Args:
            delta_years (float): Increment of time in years.

        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Tuple of (is_dead_from_age,
            new_metabolism_config_if_stage_changed).
        """
        if delta_years <= 0:
            return False, None

        old_stage = self.age_stage
        self.age_years += delta_years
        self.age_stage = self._compute_age_stage()

        prob = 0.0
        current_cfg = None
        for stage in self.age_profile:
            if stage["name"] == self.age_stage:
                prob = float(stage.get("death_prob", 0.0))
                current_cfg = stage.get("metabolism")
                break

        if prob > 0.0:
            daily_prob = prob / 365.25
            if random.random() < daily_prob:
                return True, current_cfg

        if old_stage != self.age_stage:
            return False, current_cfg
        return False, None


class MetabolismComponent:
    """Manages nutrition, caloric reserves, body mass, and carcass values.

    Attributes:
        daily_calorie_need (float): Daily energetic requirement in kcal.
        calorie_reserve_days (float): Reserve endurance capacity in days.
        max_calories (float): Maximum energetic reserve capacity.
        calories (float): Current stored calories.
        meal_calories (float): Caloric intake capacity per meal.
        base_body_mass_kg (float): Unscaled baseline body mass in kg.
        body_mass_kg (float): Scaled body mass in kg.
        carcass_edible_ratio (float): Edible mass percentage.
        carcass_calories_per_kg (float): Caloric density per kg of meat.
        body_nutrition (float): Total carcass nutritional yield.
    """

    def __init__(
        self,
        cfg: Dict[str, Any],
        initial_calories: float = 0.0,
        initial_max: float = 0.0,
        initial_body_nutrition: float = 0.0,
    ) -> None:
        """Initializes MetabolismComponent with configuration dictionary.

        Args:
            cfg (Dict[str, Any]): Metabolism configuration mapping.
            initial_calories (float): Initial calories. Defaults to 0.0.
            initial_max (float): Initial max capacity. Defaults to 0.0.
            initial_body_nutrition (float): Explicit body nutrition override.
        """
        self.daily_calorie_need = self._resolve_daily_calorie_need(cfg)
        self.calorie_reserve_days = self._coerce_positive_float(
            cfg.get("reserve_days"), fallback=3.0
        )
        self.max_calories = self.daily_calorie_need * self.calorie_reserve_days

        if initial_max > 0:
            self.calories = (
                initial_calories / initial_max
            ) * self.max_calories
        else:
            self.calories = self.max_calories

        self.meal_calories = self._resolve_meal_calories(cfg)
        self.base_body_mass_kg = self._coerce_positive_float(
            cfg.get("body_mass_kg"), fallback=0.0
        )
        self.body_mass_kg = self.base_body_mass_kg
        self.carcass_edible_ratio = self._coerce_positive_float(
            cfg.get("carcass_edible_ratio"), fallback=0.55
        )
        self.carcass_calories_per_kg = self._coerce_positive_float(
            cfg.get("carcass_calories_per_kg"), fallback=1800.0
        )
        self.body_nutrition = initial_body_nutrition

    @staticmethod
    def _coerce_positive_float(value: Any, *, fallback: float) -> float:
        """Coerces input value to a positive float or returns fallback."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number if number > 0.0 else fallback

    def _resolve_daily_calorie_need(self, cfg: Dict[str, Any]) -> float:
        """Calculates daily calorie requirement from configuration keys."""
        explicit = self._coerce_positive_float(
            cfg.get("daily_calorie_need"), fallback=0.0
        )
        if explicit > 0.0:
            return explicit
        intake_kg = self._coerce_positive_float(
            cfg.get("daily_food_intake_kg"), fallback=0.0
        )
        cals = self._coerce_positive_float(
            cfg.get("food_calories_per_kg"), fallback=0.0
        )
        if intake_kg > 0.0 and cals > 0.0:
            return intake_kg * cals
        return 2400.0

    def _resolve_meal_calories(self, cfg: Dict[str, Any]) -> float:
        """Calculates meal caloric intake capacity from configuration keys."""
        explicit = self._coerce_positive_float(
            cfg.get("meal_calories"), fallback=0.0
        )
        if explicit > 0.0:
            return explicit
        meal_kg = self._coerce_positive_float(
            cfg.get("meal_intake_kg"), fallback=0.0
        )
        cals = self._coerce_positive_float(
            cfg.get("food_calories_per_kg"), fallback=0.0
        )
        if meal_kg > 0.0 and cals > 0.0:
            return meal_kg * cals
        return 60.0

    def apply_profile(
        self,
        metabolism_cfg: Dict[str, Any],
        age_stage: str,
        sex: str,
        traits: Dict[str, Any],
    ) -> None:
        """Applies new metabolic parameters and updates body dimensions.

        Args:
            metabolism_cfg (Dict[str, Any]): Updated metabolism config mapping.
            age_stage (str): Active age stage string.
            sex (str): Sex identifier string.
            traits (Dict[str, Any]): Animal traits dictionary.
        """
        self.daily_calorie_need = self._resolve_daily_calorie_need(
            metabolism_cfg
        )
        self.calorie_reserve_days = self._coerce_positive_float(
            metabolism_cfg.get("reserve_days"),
            fallback=self.calorie_reserve_days,
        )
        self.max_calories = self.daily_calorie_need * self.calorie_reserve_days
        self.calories = min(self.calories, self.max_calories)
        self.meal_calories = self._resolve_meal_calories(metabolism_cfg)
        body_mass = self._coerce_positive_float(
            metabolism_cfg.get("body_mass_kg"), fallback=0.0
        )
        if body_mass > 0.0:
            self.base_body_mass_kg = body_mass
        self.carcass_edible_ratio = self._coerce_positive_float(
            metabolism_cfg.get("carcass_edible_ratio"),
            fallback=self.carcass_edible_ratio,
        )
        self.carcass_calories_per_kg = self._coerce_positive_float(
            metabolism_cfg.get("carcass_calories_per_kg"),
            fallback=self.carcass_calories_per_kg,
        )
        self.refresh_body_profile(age_stage, sex, traits)

    def refresh_body_profile(
        self, age_stage: str, sex: str, traits: Dict[str, Any]
    ) -> None:
        """Refreshes body mass scaling and carcass nutritional value.

        Args:
            age_stage (str): Active age stage string.
            sex (str): Sex identifier string.
            traits (Dict[str, Any]): Animal traits dictionary.
        """
        if self.base_body_mass_kg <= 0.0:
            return

        stage_scale = 1.0
        sex_scale = 1.0
        metabolism_cfg = traits.get("metabolism", {})

        if isinstance(metabolism_cfg, dict):
            stage_scales = metabolism_cfg.get("age_stage_mass_scale")
            if isinstance(stage_scales, dict):
                stage_scale = self._coerce_positive_float(
                    stage_scales.get(age_stage), fallback=1.0
                )

            sex_scales = metabolism_cfg.get("sex_mass_scale")
            if isinstance(sex_scales, dict):
                sex_scale = self._coerce_positive_float(
                    sex_scales.get(sex), fallback=1.0
                )

        self.body_mass_kg = self.base_body_mass_kg * stage_scale * sex_scale

        estimated = max(
            0.0,
            self.body_mass_kg
            * self.carcass_edible_ratio
            * self.carcass_calories_per_kg,
        )
        if estimated > 0.0:
            self.body_nutrition = estimated
