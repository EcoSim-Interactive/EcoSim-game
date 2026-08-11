"""Specialization of `Species` carrying behavioral and social state.

Provides high-level AI hooks, demographic attributes, and social states.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any, Callable, Dict, Optional, Tuple

from domain import Species
from domain.animal_components import AgeComponent, MetabolismComponent
from domain.constants import WATER_MEMORY_TTL_STEPS

from .ai import behavior as ai_behavior

LogFn = Callable[[str], None]


class Animal(Species):
    """Concrete Animal entity enriched with AI, identifiers, and social states.

    Attributes:
        animal_id (int): Unique numerical identifier.
        species_type (str): Species classification tag.
        traits (Dict[str, Any]): Trait mapping dictionary.
        sex (str): Biological sex identifier ('male', 'female', 'unknown').
        age_years (float): Active age value in years.
        age_stage (str): Active age stage string ('juvenile', 'adult', etc.).
        display_name (str): Computed user-friendly display name.
        group_id (Optional[str]): Active group identifier tag.
        pack_id (Optional[str]): Active pack identifier tag.
        group_state (Dict[str, Any]): Shared state dict for active group.
        pack_state (Dict[str, Any]): Shared state dict for active pack.
        social_state (Dict[str, Any]): Individual social memory.
        territory_anchor (Optional[Tuple[float, float]]): Territory center.
    """

    _id_sequence = itertools.count(1)

    _pack_states: dict[str, dict[str, Any]] = {}
    _group_states: dict[str, dict[str, Any]] = {}

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
        *,
        species_type: str | None = None,
        animal_id: int | None = None,
        traits: Optional[Dict[str, Any]] = None,
        group_id: Optional[str] = None,
        pack_id: Optional[str] = None,
        age_years: Optional[float] = None,
    ) -> None:
        """Initializes Animal instance with spatial, physical, and AI traits.

        Args:
            name (str): Entity name.
            position (Tuple[float, float]): Initial (x, y) coordinates.
            vision (float): Vision perception radius in meters.
            smell_range (float): Olfactory perception range.
            speed (float): Movement speed per step.
            diurnal (bool): Active during daytime if True.
            temperament (str): Temperament classification string.
            diet (str): Diet classification ('herbivore', 'carnivore', etc.).
            body_nutrition (float): Edible carcass nutritional yield.
            species_type (Optional[str]): Species category label.
            animal_id (Optional[int]): Explicit ID override.
            traits (Optional[Dict[str, Any]]): Trait configuration dictionary.
            group_id (Optional[str]): Social group ID tag.
            pack_id (Optional[str]): Predator pack ID tag.
            age_years (Optional[float]): Initial age override in years.
        """
        traits_copy: Dict[str, Any] = (
            copy.deepcopy(traits) if isinstance(traits, dict) else {}
        )
        initial_age = self._coerce_age_value(
            traits_copy.get("age_years", age_years)
        )
        metabolism_cfg = (
            traits_copy.get("metabolism")
            if isinstance(traits_copy.get("metabolism"), dict)
            else {}
        )
        temp_metabolism = MetabolismComponent(
            metabolism_cfg, initial_body_nutrition=body_nutrition
        )
        super().__init__(
            name=name,
            position=position,
            vision=vision,
            smell_range=smell_range,
            speed=speed,
            diurnal=diurnal,
            temperament=temperament,
            diet=diet,
            body_nutrition=body_nutrition,
            age_years=initial_age,
            daily_calorie_need=temp_metabolism.daily_calorie_need,
            calorie_reserve_days=temp_metabolism.calorie_reserve_days,
            meal_calories=temp_metabolism.meal_calories,
            body_mass_kg=temp_metabolism.base_body_mass_kg or None,
            carcass_edible_ratio=temp_metabolism.carcass_edible_ratio,
            carcass_calories_per_kg=temp_metabolism.carcass_calories_per_kg,
            sprite_name=traits_copy.get("sprite_name"),
        )
        self._metabolism_comp = temp_metabolism
        self.original_name = name
        self.animal_id = (
            animal_id if animal_id is not None else next(self._id_sequence)
        )
        self.species_type = species_type or name
        self.traits = traits_copy
        self.age_years = self._coerce_age_value(
            self.traits.get("age_years", self.age_years)
        )
        self.traits["age_years"] = self.age_years
        self.age_units = "years"
        self.age_profile_spec = (
            copy.deepcopy(self.traits.get("age_profile"))
            if isinstance(self.traits.get("age_profile"), dict)
            else None
        )
        self.age_profile = self._normalize_age_profile(self.age_profile_spec)
        if self.age_profile_spec is not None:
            self.traits["age_profile"] = copy.deepcopy(self.age_profile_spec)
        explicit_age_stage = (
            self._normalize_stage(self.traits.get("age_stage"))
            if self.traits.get("age_stage") is not None
            else None
        )
        self.age_stage = explicit_age_stage or self._compute_age_stage()
        self.traits["age_stage"] = self.age_stage
        self.sex = self._normalize_sex(self.traits.get("sex"))
        self.traits["sex"] = self.sex
        self.display_name = self._compute_display_name()
        self.name = self.display_name
        self.traits["display_name"] = self.display_name
        self.refresh_body_profile()
        self.group_id = group_id or self.traits.get("group_id")
        if self.group_id:
            self.group_state = self._group_states.setdefault(
                str(self.group_id), {}
            )
            self.traits["group_id"] = self.group_id
        else:
            self.group_state = {}
            self.traits.pop("group_id", None)
        self.pack_id = pack_id or self.traits.get("pack_id")
        if self.pack_id:
            self.pack_state = self._pack_states.setdefault(
                str(self.pack_id), {}
            )
            self.traits["pack_id"] = self.pack_id
        else:
            self.pack_state = {}
            self.traits.pop("pack_id", None)
        self.water_memory: Optional[Dict[str, float]] = None
        self.water_memory_ttl = 0
        self.social_state: Dict[str, Any] = {}
        self.territory_anchor: Optional[Tuple[float, float]] = None
        territory_cfg = self.traits.get("territory")
        if isinstance(territory_cfg, dict):
            center = territory_cfg.get("center")
            if isinstance(center, (list, tuple)) and len(center) >= 2:
                self.territory_anchor = (float(center[0]), float(center[1]))
            else:
                self.territory_anchor = (self.x, self.y)

    @classmethod
    def from_species(
        cls, species: Species, *, species_type: str | None = None
    ) -> "Animal":
        """Creates an Animal instance from an existing Species instance.

        Args:
            species (Species): Source base Species object.
            species_type (Optional[str]): Optional species category override.

        Returns:
            Animal: Fully configured Animal object.
        """
        if isinstance(species, cls):
            if species_type is not None:
                species.set_species_type(species_type)
            return species

        instance = cls(
            name=species.name,
            position=(species.x, species.y),
            vision=species.vision,
            smell_range=species.smell_range,
            speed=species.speed,
            diurnal=species.diurnal,
            temperament=species.temperament,
            diet=species.diet,
            body_nutrition=species.body_nutrition,
            species_type=species_type
            or getattr(species, "species_type", species.name),
            animal_id=getattr(species, "animal_id", None),
            traits=getattr(species, "traits", None),
            group_id=getattr(species, "group_id", None),
            pack_id=getattr(species, "pack_id", None),
        )

        instance.original_name = getattr(
            species, "original_name", species.name
        )
        instance.vitality = species.vitality
        instance.consumed = species.consumed
        instance.memory = species.memory
        instance.rest_steps = species.rest_steps
        instance.max_rest_steps = species.max_rest_steps
        instance.daily_calorie_need = getattr(
            species, "daily_calorie_need", instance.daily_calorie_need
        )
        instance.calorie_reserve_days = getattr(
            species, "calorie_reserve_days", instance.calorie_reserve_days
        )
        instance.max_calories = getattr(
            species, "max_calories", instance.max_calories
        )
        instance.calories = getattr(species, "calories", instance.calories)
        instance.meal_calories = getattr(
            species, "meal_calories", instance.meal_calories
        )
        instance.base_body_mass_kg = getattr(
            species, "base_body_mass_kg", instance.base_body_mass_kg
        )
        instance.body_mass_kg = getattr(
            species, "body_mass_kg", instance.body_mass_kg
        )
        instance.carcass_edible_ratio = getattr(
            species, "carcass_edible_ratio", instance.carcass_edible_ratio
        )
        instance.carcass_calories_per_kg = getattr(
            species,
            "carcass_calories_per_kg",
            instance.carcass_calories_per_kg,
        )
        instance.body_nutrition = getattr(
            species, "body_nutrition", instance.body_nutrition
        )
        instance.thirst = species.thirst
        instance.fatigue = species.fatigue
        instance.resting = species.resting
        instance.alive = species.alive
        instance.social_state = dict(getattr(species, "social_state", {}))
        instance.territory_anchor = getattr(species, "territory_anchor", None)
        if instance.pack_id:
            instance.pack_state = cls._pack_states.setdefault(
                str(instance.pack_id), {}
            )
        if instance.group_id:
            instance.group_state = cls._group_states.setdefault(
                str(instance.group_id), {}
            )
        instance.sex = getattr(species, "sex", instance.sex)
        instance.age_years = getattr(species, "age_years", instance.age_years)
        instance.age_profile_spec = copy.deepcopy(
            getattr(species, "age_profile_spec", instance.age_profile_spec)
        )
        instance.age_profile = copy.deepcopy(
            getattr(species, "age_profile", instance.age_profile)
        )
        instance.age_units = getattr(
            species, "age_units", getattr(instance, "age_units", "years")
        )
        instance.age_stage = getattr(
            species, "age_stage", instance._compute_age_stage()
        )
        instance.traits["sex"] = instance.sex
        instance.traits["age_years"] = instance.age_years
        instance.traits["age_stage"] = instance.age_stage
        instance.traits["display_name"] = instance.display_name
        instance.display_name = instance._compute_display_name()
        instance.name = instance.display_name
        return instance

    @property
    def position(self) -> Tuple[float, float]:
        """Gets current (x, y) spatial position coordinates."""
        return (self.x, self.y)

    @position.setter
    def position(self, pos: Tuple[float, float]) -> None:
        """Sets spatial position coordinates."""
        self.x, self.y = pos

    @property
    def id(self) -> int:
        """Unique numerical identifier of the animal."""
        return self.animal_id

    def get_traits(self) -> Dict[str, Any]:
        """Returns a copy of the animal's trait dictionary."""
        return copy.deepcopy(self.traits)

    def update_traits(self, updates: Dict[str, Any]) -> None:
        """Updates multiple traits in bulk.

        Args:
            updates (Dict[str, Any]): Dictionary of trait key-value pairs.
        """
        if not isinstance(updates, dict):
            return
        for key, value in updates.items():
            self.set_trait(key, value)

    def get_trait(self, key: str, default: Any = None) -> Any:
        """Gets trait value by key with optional fallback.

        Args:
            key (str): Trait key string.
            default (Any): Fallback value if key is missing.

        Returns:
            Any: Trait value or fallback.
        """
        return self.traits.get(key, default)

    def set_trait(self, key: str, value: Any) -> None:
        """Sets single trait value and refreshes internal state components.

        Args:
            key (str): Trait key identifier.
            value (Any): Trait value payload.
        """
        if key == "sex":
            self.set_sex(value)
            return
        if key == "age_stage":
            self.set_age_stage(value)
            return
        if key == "age_years":
            self.set_age_years(value)
            return
        if key == "age_profile":
            if isinstance(value, dict):
                self.age_profile_spec = copy.deepcopy(value)
                self.traits["age_profile"] = copy.deepcopy(value)
            else:
                self.age_profile_spec = None
                if value is None:
                    self.traits.pop("age_profile", None)
                else:
                    self.traits["age_profile"] = value
            self.age_profile = self._normalize_age_profile(
                self.age_profile_spec
            )
            self.age_stage = self._compute_age_stage()
            self.traits["age_stage"] = self.age_stage
            self.refresh_body_profile()
            self.display_name = self._compute_display_name()
            self.name = self.display_name
            self.traits["display_name"] = self.display_name
            return
        if key == "group_id":
            self.set_group_id(value)
            return
        if key == "pack_id":
            self.set_pack_id(value)
            return
        if key == "naming":
            if isinstance(value, dict):
                self.traits[key] = copy.deepcopy(value)
            else:
                self.traits[key] = value
            self.display_name = self._compute_display_name()
            self.name = self.display_name
            self.traits["display_name"] = self.display_name
            return
        if key == "metabolism":
            if isinstance(value, dict):
                self.traits[key] = copy.deepcopy(value)
                self._apply_metabolism_profile(self.traits[key])
            else:
                self.traits[key] = value
            return
        if isinstance(value, dict):
            self.traits[key] = copy.deepcopy(value)
        else:
            self.traits[key] = value

    def get_group_id(self) -> Optional[str]:
        """Gets active group identifier tag."""
        return self.group_id

    def set_group_id(self, value: Optional[str]) -> None:
        """Sets group identifier and binds shared group state dictionary.

        Args:
            value (Optional[str]): Group identifier string.
        """
        self.group_id = value
        if value:
            self.group_state = self._group_states.setdefault(str(value), {})
            self.traits["group_id"] = value
        else:
            self.group_state = {}
            self.traits.pop("group_id", None)

    def get_pack_id(self) -> Optional[str]:
        """Gets active pack identifier tag."""
        return self.pack_id

    def set_pack_id(self, value: Optional[str]) -> None:
        """Sets pack identifier and binds shared pack state dictionary.

        Args:
            value (Optional[str]): Pack identifier string.
        """
        self.pack_id = value
        if value:
            self.pack_state = self._pack_states.setdefault(str(value), {})
            self.traits["pack_id"] = value
        else:
            self.pack_state = {}
            self.traits.pop("pack_id", None)

    def remember_social(self, key: str, value: Any) -> None:
        """Stores transient social memory entry.

        Args:
            key (str): Memory entry key string.
            value (Any): Memory entry payload.
        """
        self.social_state[key] = value

    def recall_social(self, key: str, default: Any = None) -> Any:
        """Recalls transient social memory entry.

        Args:
            key (str): Memory entry key string.
            default (Any): Fallback value if memory key is missing.

        Returns:
            Any: Memory value or fallback.
        """
        return self.social_state.get(key, default)

    def remember_water(
        self, x: float, y: float, ttl_steps: int = WATER_MEMORY_TTL_STEPS
    ) -> None:
        """Stores remembered water source location with step TTL decay.

        Args:
            x (float): X coordinate.
            y (float): Y coordinate.
            ttl_steps (int): TTL duration in simulation steps.
        """
        try:
            self.water_memory = {"x": float(x), "y": float(y)}
            self.water_memory_ttl = max(0, int(ttl_steps))
        except (TypeError, ValueError):
            return

    def remember_water_target(self, x: float, y: float) -> None:
        """Stores precise bank tile coordinates for water approach.

        Args:
            x (float): Bank target X coordinate.
            y (float): Bank target Y coordinate.
        """
        if not self.water_memory or self.water_memory_ttl <= 0:
            return
        try:
            self.water_memory["target_x"] = float(x)
            self.water_memory["target_y"] = float(y)
        except (TypeError, ValueError):
            return

    def recall_water_target(self) -> Optional[Tuple[float, float]]:
        """Recalls target bank tile coordinates if memory is active.

        Returns:
            Optional[Tuple[float, float]]: (target_x, target_y) or None.
        """
        if not self.water_memory or self.water_memory_ttl <= 0:
            return None
        target_x = self.water_memory.get("target_x")
        target_y = self.water_memory.get("target_y")
        if target_x is None or target_y is None:
            return None
        return (float(target_x), float(target_y))

    def clear_water_target(self) -> None:
        """Clears active bank target tile coordinates from memory."""
        if not self.water_memory:
            return
        self.water_memory.pop("target_x", None)
        self.water_memory.pop("target_y", None)

    def recall_water(self) -> Optional[Tuple[float, float]]:
        """Recalls remembered water location coordinates if memory is active.

        Returns:
            Optional[Tuple[float, float]]: (x, y) coordinates or None.
        """
        if not self.water_memory or self.water_memory_ttl <= 0:
            return None
        return (
            float(self.water_memory.get("x", 0.0)),
            float(self.water_memory.get("y", 0.0)),
        )

    def _tick_water_memory(self) -> None:
        """Decrements water memory TTL timer and clears memory upon expiry."""
        if self.water_memory_ttl > 0:
            self.water_memory_ttl -= 1
            if self.water_memory_ttl <= 0:
                self.water_memory = None

    @classmethod
    def pack_state_for(cls, pack_id: str) -> Dict[str, Any]:
        """Gets or initializes shared pack state mapping by pack ID.

        Args:
            pack_id (str): Pack identifier string.

        Returns:
            Dict[str, Any]: Shared pack state dictionary.
        """
        return cls._pack_states.setdefault(str(pack_id), {})

    @classmethod
    def group_state_for(cls, group_id: str) -> Dict[str, Any]:
        """Gets or initializes shared group state mapping by group ID.

        Args:
            group_id (str): Group identifier string.

        Returns:
            Dict[str, Any]: Shared group state dictionary.
        """
        return cls._group_states.setdefault(str(group_id), {})

    @classmethod
    def reset_shared_states(cls) -> None:
        """Clears all shared pack and group state dictionaries."""
        cls._pack_states.clear()
        cls._group_states.clear()

    def _normalize_sex(self, value: Any) -> str:
        """Normalizes raw sex string input to standard male/female string."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"male", "m", "masc"}:
                return "male"
            if lowered in {"female", "f", "fem"}:
                return "female"
            if lowered:
                return lowered
        return "unknown"

    def _normalize_stage(self, value: Any) -> str:
        """Normalizes raw age stage input string."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered:
                return lowered
        return "adult"

    def _coerce_age_value(self, value: Any) -> float:
        """Coerces raw age value to positive float."""
        try:
            age = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, age)

    def _coerce_positive_float(self, value: Any, *, fallback: float) -> float:
        """Coerces input to positive float or returns fallback."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number if number > 0.0 else fallback

    def refresh_body_profile(self) -> None:
        """Updates body mass and caloric value according to active profile."""
        if not hasattr(self, "_metabolism_comp"):
            metabolism_cfg = (
                self.traits.get("metabolism", {})
                if hasattr(self, "traits") and isinstance(self.traits, dict)
                else {}
            )
            self._metabolism_comp = MetabolismComponent(
                metabolism_cfg,
                initial_calories=self.calories,
                initial_max=getattr(self, "max_calories", 0.0),
            )
        self._metabolism_comp.refresh_body_profile(
            self.age_stage, self.sex, getattr(self, "traits", {})
        )
        self.body_mass_kg = self._metabolism_comp.body_mass_kg
        self.body_nutrition = self._metabolism_comp.body_nutrition

    def _apply_metabolism_profile(
        self, metabolism_cfg: Dict[str, Any]
    ) -> None:
        """Applies updated metabolism configuration payload."""
        if not hasattr(self, "_metabolism_comp"):
            self._metabolism_comp = MetabolismComponent(
                metabolism_cfg,
                initial_calories=self.calories,
                initial_max=getattr(self, "max_calories", 0.0),
            )

        current_percent = (
            self.calories / self.max_calories
            if getattr(self, "max_calories", 0.0) > 0
            else 1.0
        )

        self._metabolism_comp.apply_profile(
            metabolism_cfg,
            self.age_stage,
            self.sex,
            getattr(self, "traits", {}),
        )
        self.daily_calorie_need = self._metabolism_comp.daily_calorie_need
        self.calorie_reserve_days = self._metabolism_comp.calorie_reserve_days
        self.max_calories = self._metabolism_comp.max_calories
        self.calories = min(
            self.max_calories, self.max_calories * current_percent
        )
        self.meal_calories = self._metabolism_comp.meal_calories
        self.base_body_mass_kg = self._metabolism_comp.base_body_mass_kg
        self.carcass_edible_ratio = self._metabolism_comp.carcass_edible_ratio
        self.carcass_calories_per_kg = (
            self._metabolism_comp.carcass_calories_per_kg
        )
        self.body_mass_kg = self._metabolism_comp.body_mass_kg
        self.body_nutrition = self._metabolism_comp.body_nutrition

    def _normalize_age_profile(self, spec: Any) -> list[Dict[str, Any]]:
        """Instantiates AgeComponent to normalize stage list."""
        self._age_comp = AgeComponent(getattr(self, "age_years", 0.0), spec)
        self.age_units = self._age_comp.age_units
        return self._age_comp.age_profile

    def _compute_age_stage(self) -> str:
        """Computes active age stage from internal AgeComponent."""
        if hasattr(self, "_age_comp"):
            return self._age_comp.age_stage
        return "adult"

    def _extract_label(self, source: Any) -> Optional[str]:
        """Extracts display label from raw string or dictionary by sex key."""
        if isinstance(source, str):
            return source
        if isinstance(source, dict):
            if self.sex in source and isinstance(source[self.sex], str):
                return source[self.sex]
            if "default" in source and isinstance(source["default"], str):
                return source["default"]
        return None

    def _compute_display_name(self) -> str:
        """Computes user-facing display name based on naming traits."""
        naming = self.traits.get("naming", {})
        label: Optional[str] = None
        if isinstance(naming, dict):
            label = self._extract_label(naming.get(self.age_stage))
            if label is None:
                label = self._extract_label(naming.get("default"))
            if label is None:
                label = self._extract_label(naming.get(self.sex))
        if not label:
            base = (
                self.species_type
                if isinstance(self.species_type, str)
                else self.original_name
            )
            label = str(base)
        return label

    def get_display_name(self) -> str:
        """Gets user-facing display name."""
        return self.display_name

    def set_sex(self, value: str) -> None:
        """Sets biological sex and refreshes body mass and display name.

        Args:
            value (str): Sex string ('male', 'female', etc.).
        """
        self.sex = self._normalize_sex(value)
        self.traits["sex"] = self.sex
        self.refresh_body_profile()
        self.display_name = self._compute_display_name()
        self.name = self.display_name
        self.traits["display_name"] = self.display_name

    def set_age_stage(self, value: str) -> None:
        """Sets age stage string and refreshes body profile.

        Args:
            value (str): Age stage string ('juvenile', 'adult', etc.).
        """
        self.age_stage = self._normalize_stage(value)
        self.traits["age_stage"] = self.age_stage
        self.refresh_body_profile()
        self.display_name = self._compute_display_name()
        self.name = self.display_name
        self.traits["display_name"] = self.display_name

    def set_age_years(self, value: float) -> None:
        """Updates entity age in years and evaluates stage transitions.

        Args:
            value (float): Target age value in years.
        """
        try:
            new_val = max(0.0, float(value))
        except (TypeError, ValueError):
            return
        if new_val <= self.age_years:
            return

        delta = new_val - self.age_years

        if not hasattr(self, "_age_comp"):
            self._age_comp = AgeComponent(
                self.age_years, self.age_profile_spec
            )

        is_dead, metabolism_cfg = self._age_comp.tick_age(delta)

        self.age_years = self._age_comp.age_years
        old_stage = self.age_stage
        self.age_stage = self._age_comp.age_stage

        if is_dead:
            self.alive = False
            return

        if old_stage != self.age_stage:
            self.traits["age_stage"] = self.age_stage
            if metabolism_cfg:
                self._apply_metabolism_profile(metabolism_cfg)
            else:
                self.refresh_body_profile()

    def advance_age(self, minutes_per_step: float) -> None:
        """Advances entity age proportional to step duration.

        Args:
            minutes_per_step (float): Step duration in minutes.
        """
        try:
            minutes = float(minutes_per_step)
        except (TypeError, ValueError):
            return
        if minutes <= 0:
            return
        years_increment = minutes / (60.0 * 24.0 * 365.25)
        if years_increment <= 0:
            return
        self.set_age_years(self.age_years + years_increment)

    def update_vitals(self, world_time: Dict[str, float]) -> None:
        """Updates internal vital indicators and ticks water memory TTL.

        Args:
            world_time (Dict[str, float]): World time payload.
        """
        super().update_vitals(world_time)
        self._tick_water_memory()

    def decide_idle_action(self) -> str:
        """Delegates idle action selection to AI behavior module."""
        return ai_behavior.decide_idle_action(self)

    def handle_thirst(self, world: Any, log: LogFn) -> Tuple[bool, str, str]:
        """Delegates thirst handling to AI behavior module."""
        return ai_behavior.handle_thirst(self, world, log)

    def handle_fatigue(self, log: LogFn) -> Tuple[bool, str, str]:
        """Delegates fatigue handling to AI behavior module."""
        return ai_behavior.handle_fatigue(self, log)

    def handle_cycle_rest(self, log: LogFn) -> Tuple[bool, str, str]:
        """Delegates rest cycle handling to AI behavior module."""
        return ai_behavior.handle_cycle_rest(self, log)

    def handle_hunger(self, world: Any, log: LogFn) -> Tuple[bool, str, str]:
        """Delegates hunger handling to AI behavior module."""
        return ai_behavior.handle_hunger(self, world, log)

    def handle_idle(self, world: Any, log: LogFn) -> Tuple[str, str]:
        """Delegates idle state handling to AI behavior module."""
        return ai_behavior.handle_idle(self, world, log)


def decide_idle_action(species: Animal) -> str:
    """Wrapper function for decide_idle_action."""
    return species.decide_idle_action()


def handle_thirst(
    species: Animal, world: Any, log: LogFn
) -> Tuple[bool, str, str]:
    """Wrapper function for handle_thirst."""
    return species.handle_thirst(world, log)


def handle_fatigue(species: Animal, log: LogFn) -> Tuple[bool, str, str]:
    """Wrapper function for handle_fatigue."""
    return species.handle_fatigue(log)


def handle_cycle_rest(species: Animal, log: LogFn) -> Tuple[bool, str, str]:
    """Wrapper function for handle_cycle_rest."""
    return species.handle_cycle_rest(log)


def handle_hunger(
    species: Animal, world: Any, log: LogFn
) -> Tuple[bool, str, str]:
    """Wrapper function for handle_hunger."""
    return species.handle_hunger(world, log)


def handle_idle(species: Animal, world: Any, log: LogFn) -> Tuple[str, str]:
    """Wrapper function for handle_idle."""
    return species.handle_idle(world, log)
