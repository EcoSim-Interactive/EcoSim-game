"""Loads world environment and animal species population from JSON files."""

from __future__ import annotations

import copy
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from domain import World
from simulation.animal import Animal

logger = logging.getLogger(__name__)

SPECIES_PRESETS_DIR = Path(__file__).with_name("species")

if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).parent.resolve()

DEFAULT_CONFIG_PATH = APP_ROOT / "app" / "world_config.json"


def load_world(
    config_path: Optional[str] = None,
    *,
    fallback_food: int = 30,
    fallback_water: int = 10,
) -> World:
    """Loads World instance from JSON config file or falls back to defaults.

    Args:
        config_path (Optional[str]): Path to world_config.json file.
        fallback_food (int): Quantity of food if config fails.
        fallback_water (int): Quantity of water if config fails.

    Returns:
        World: Configured or fallback World instance.
    """
    try:
        config, base_dir = load_config(config_path)
        return build_world_from_config(config, base_dir=base_dir)
    except FileNotFoundError:
        logger.warning(
            "World configuration file not found, using fallback generation."
        )
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "Invalid world configuration, using fallback generation: %s", exc
        )

    return _build_default_world(fallback_food, fallback_water)


def load_world_and_species(
    config_path: Optional[str] = None,
    *,
    fallback_food: int = 30,
    fallback_water: int = 10,
) -> Tuple[World, List[Animal]]:
    """Loads both World and Animal species population simultaneously.

    Args:
        config_path (Optional[str]): Path to world_config.json file.
        fallback_food (int): Quantity of food if config fails.
        fallback_water (int): Quantity of water if config fails.

    Returns:
        Tuple[World, List[Animal]]: Tuple containing World and Animal list.
    """
    try:
        config, base_dir = load_config(config_path)
        world = build_world_from_config(config, base_dir=base_dir)
        species_list = build_species_from_config(
            config, world, base_dir=base_dir
        )
        if not species_list:
            species_list = _build_default_species(world)
        return world, species_list
    except FileNotFoundError:
        logger.warning(
            "World configuration file not found, using fallback generation."
        )
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "Invalid world configuration, using fallback generation: %s", exc
        )

    world = _build_default_world(fallback_food, fallback_water)
    species_list = _build_default_species(world)
    return world, species_list


def load_world_from_file(config_path: Optional[str] = None) -> World:
    """Loads World instance strictly from JSON file.

    Args:
        config_path (Optional[str]): Path to world_config.json file.

    Returns:
        World: Constructed World domain object.
    """
    config, base_dir = load_config(config_path)
    return build_world_from_config(config, base_dir=base_dir)


def load_config(
    config_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Path]:
    """Reads JSON config file and returns dict with base directory.

    Args:
        config_path (Optional[str]): Target configuration file path.

    Returns:
        Tuple[Dict[str, Any], Path]: Tuple of (config_dict, base_dir_path).

    Raises:
        ValueError: If file content is not a valid JSON dictionary.
    """
    resolved = _resolve_config_path(config_path)

    print(f"DEBUG: Chargement JSON depuis : {resolved}")

    with resolved.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(
            f"Le fichier {resolved.name} doit contenir un objet JSON."
        )

    return data, resolved.parent


def build_world_from_config(
    config: Dict[str, Any], *, base_dir: Optional[Path] = None
) -> World:
    """Constructs World instance from configuration mapping.

    Args:
        config (Dict[str, Any]): Parsed JSON configuration mapping.
        base_dir (Optional[Path]): Base path for relative resource resolution.

    Returns:
        World: Configured World instance.
    """
    world_cfg = config.get("world", {})
    width = _positive_int(world_cfg.get("width")) or 1000
    height = _positive_int(world_cfg.get("height")) or 1000
    minutes_per_step = _positive_int(world_cfg.get("minutes_per_step")) or 10

    world = World(
        width=width, height=height, minutes_per_step=minutes_per_step
    )

    apply_water_config(world, config.get("water"))
    apply_food_config(world, config.get("food"))
    return world


def build_species_from_config(
    config: Dict[str, Any],
    world: World,
    *,
    base_dir: Optional[Path] = None,
) -> List[Animal]:
    """Constructs species list from presets and population specs.

    Args:
        config (Dict[str, Any]): Parsed JSON configuration mapping.
        world (World): World instance for spatial clamping and placement.
        base_dir (Optional[Path]): Base path for preset resolution.

    Returns:
        List[Animal]: Initialized Animal instances.
    """
    section = config.get("species")
    if not isinstance(section, dict):
        return []

    defaults = section.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}

    population = section.get("population")
    species_list: List[Animal] = []
    combined_entries: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []

    if isinstance(population, list):
        for entry in population:
            if isinstance(entry, dict):
                defaults_chain = (
                    [defaults] if isinstance(defaults, dict) else []
                )
                combined_entries.append((entry, list(defaults_chain)))

    presets = section.get("presets")
    if isinstance(presets, list):
        for preset_spec in presets:
            if isinstance(preset_spec, dict):
                preset_ref = (
                    preset_spec.get("preset")
                    or preset_spec.get("path")
                    or preset_spec.get("file")
                )
                instances_raw = preset_spec.get("instances")
                overrides = preset_spec.get("overrides")
                instances = [
                    inst
                    for inst in instances_raw or []
                    if isinstance(inst, dict)
                ]
            else:
                preset_ref = preset_spec
                overrides = None
                instances = []

            preset_data = _load_species_preset(preset_ref, base_dir)
            if not preset_data:
                continue
            preset_defaults = {
                k: v
                for k, v in preset_data.items()
                if k not in {"population", "instances"}
            }
            if isinstance(overrides, dict):
                merged_overrides = dict(overrides)
                if "traits" in overrides and isinstance(
                    overrides["traits"], dict
                ):
                    base_traits = _extract_traits(
                        preset_defaults.get("traits")
                    )
                    override_traits = _extract_traits(overrides.get("traits"))
                    merged_traits = dict(base_traits)
                    merged_traits.update(override_traits)
                    merged_overrides["traits"] = merged_traits
                preset_defaults.update(merged_overrides)

            default_chain = [dict(preset_defaults)]
            if isinstance(defaults, dict):
                default_chain.append(defaults)

            if instances:
                for entry in instances:
                    combined_entries.append((entry, list(default_chain)))
            else:
                combined_entries.append((preset_defaults, list(default_chain)))

    if not combined_entries:
        return []

    for index, (entry, default_chain) in enumerate(combined_entries, start=1):
        if not isinstance(entry, dict):
            continue

        name_base = (
            _coerce_str(entry.get("name"))
            or _resolve_str_from_chain("name", default_chain)
            or f"Espece_{index}"
        )

        vision = _resolve_float_attr(
            "vision", entry, default_chain, fallback=80.0
        )
        smell_range = _resolve_float_attr(
            "smell_range", entry, default_chain, fallback=200.0
        )
        speed = _resolve_float_attr(
            "speed", entry, default_chain, fallback=10.0
        )
        diurnal = _resolve_bool_attr(
            "diurnal", entry, default_chain, fallback=True
        )
        temperament = (
            _coerce_str(entry.get("temperament"))
            or _resolve_str_from_chain("temperament", default_chain)
            or "neutre"
        )
        diet = (
            _coerce_str(entry.get("diet"))
            or _resolve_str_from_chain("diet", default_chain)
            or "omnivore"
        )
        body_nutrition = _resolve_float_attr(
            "body_nutrition", entry, default_chain, fallback=None
        )
        body_nutrition_range = _resolve_float_range_attr(
            "body_nutrition", entry, default_chain
        )

        requested_count = _positive_int(entry.get("count"))
        if requested_count is None:
            for defaults_source in default_chain:
                requested_count = _positive_int(
                    _extract_from_dict(defaults_source, "count")
                )
                if requested_count:
                    break
        count = requested_count or 1

        explicit_positions = _extract_positions(world, entry.get("positions"))
        if not explicit_positions:
            for defaults_source in default_chain:
                explicit_positions.extend(
                    _extract_positions(
                        world, _extract_from_dict(defaults_source, "positions")
                    )
                )
        position_candidates = [entry.get("position")]
        for defaults_source in default_chain:
            position_candidates.append(
                _extract_from_dict(defaults_source, "position")
            )
        base_position = _extract_position(world, *position_candidates)
        if explicit_positions:
            positions = explicit_positions
        else:
            positions = _build_spawn_positions(world, base_position, count)

        if len(positions) > count:
            positions = positions[:count]
        elif len(positions) < count and positions:
            positions.extend([positions[-1]] * (count - len(positions)))

        species_type = (
            _coerce_str(entry.get("species_type"))
            or _resolve_str_from_chain("species_type", default_chain)
            or _coerce_str(entry.get("species"))
            or _resolve_str_from_chain("species", default_chain)
            or _resolve_str_from_chain("name", default_chain)
            or name_base
        )

        auto_id = f"{species_type}_{index}"
        group_id = (
            _coerce_str(entry.get("group_id"))
            or _resolve_str_from_chain("group_id", default_chain)
            or f"group_{auto_id}"
        )
        traits = _resolve_traits(entry, default_chain)

        pack_id = (
            _coerce_str(entry.get("pack_id"))
            or _resolve_str_from_chain("pack_id", default_chain)
        )
        if not pack_id and (
            _resolve_str_from_chain("diet", default_chain) == "carnivore"
            or entry.get("diet") == "carnivore"
            or traits.get("predator")
            or "hunt" in traits
        ):
            pack_id = f"pack_{auto_id}"

        sex_value = _coerce_str(entry.get("sex")) or _resolve_str_from_chain(
            "sex", default_chain
        )
        age_stage_value = (
            _coerce_str(entry.get("age_stage"))
            or _resolve_str_from_chain("age_stage", default_chain)
            or "adult"
        )
        sprite_name_value = _coerce_str(
            entry.get("sprite_name")
        ) or _resolve_str_from_chain("sprite_name", default_chain)

        males_count = _positive_int(entry.get("males"))
        females_count = _positive_int(entry.get("females"))

        for offset in range(count):
            final_name = (
                name_base if count == 1 else f"{name_base}_{offset + 1}"
            )
            position = (
                positions[offset] if offset < len(positions) else positions[-1]
            )
            traits_payload = copy.deepcopy(traits)
            nutrition_value = body_nutrition
            if body_nutrition_range is not None:
                nutrition_value = random.uniform(
                    body_nutrition_range[0], body_nutrition_range[1]
                )

            current_sex = sex_value
            if not current_sex:
                if males_count is not None and females_count is not None:
                    current_sex = "male" if offset < males_count else "female"
                else:
                    current_sex = "male" if offset % 2 == 0 else "female"

            if current_sex and "sex" not in traits_payload:
                traits_payload["sex"] = current_sex
            if age_stage_value and "age_stage" not in traits_payload:
                traits_payload["age_stage"] = age_stage_value
            if sprite_name_value and "sprite_name" not in traits_payload:
                traits_payload["sprite_name"] = sprite_name_value
            species_list.append(
                Animal(
                    name=final_name,
                    position=position,
                    vision=vision,
                    smell_range=smell_range,
                    speed=speed,
                    diurnal=diurnal,
                    temperament=temperament,
                    diet=diet,
                    body_nutrition=nutrition_value,
                    species_type=species_type,
                    traits=traits_payload,
                    group_id=group_id,
                    pack_id=pack_id,
                )
            )
    return species_list


def apply_food_config(world: World, section: Any) -> None:
    """Applies food source configuration to World instance.

    Args:
        world (World): World instance to populate with food.
        section (Any): Parsed food section from JSON config.
    """
    if not isinstance(section, dict):
        return

    from domain.food_generation import DEFAULT_FOOD_PROFILES

    profiles = copy.deepcopy(DEFAULT_FOOD_PROFILES)
    presets = section.get("presets")
    if isinstance(presets, dict):
        base_dir = Path(__file__).parent.resolve()
        for key, val in presets.items():
            preset_data = val
            if isinstance(val, str):
                loaded = _load_species_preset(val, base_dir)
                if loaded:
                    preset_data = loaded

            if isinstance(preset_data, dict):
                if key in profiles:
                    profiles[key].update(preset_data)
                else:
                    profiles[key] = preset_data

    placements = section.get("placements")
    if isinstance(placements, list):
        world.add_food_placements(placements, profiles=profiles)

    distribution = _extract_distribution(section.get("distribution"))
    if distribution:
        world.add_food(distribution=distribution, profiles=profiles)

    quantity_value = _positive_int(section.get("quantity"))
    type_weights = _extract_type_weights(section.get("type_weights"))
    if quantity_value:
        world.add_food(
            quantity=quantity_value,
            type_weights=type_weights,
            profiles=profiles,
        )
    elif type_weights:
        world.add_food(type_weights=type_weights, profiles=profiles)


def apply_water_config(world: World, section: Any) -> None:
    """Applies water resource configuration to World instance.

    Args:
        world (World): World instance to populate with water features.
        section (Any): Parsed water section from JSON config.
    """
    if not isinstance(section, dict):
        return

    placements = section.get("placements")
    if isinstance(placements, list):
        world.add_water_placements(placements)

    quantity_value = _positive_int(section.get("quantity"))
    if quantity_value:
        world.add_water(
            quantity=quantity_value,
            river_segments=_positive_int(section.get("river_segments")),
            stagnant_count=_positive_int(section.get("stagnant_count")),
            oasis_count=_positive_int(section.get("oasis_count")),
            lake_count=_positive_int(section.get("lake_count")),
            fill_step=_positive_int(section.get("fill_step")),
        )


def _build_default_world(fallback_food: int, fallback_water: int) -> World:
    """Constructs default World instance with fallback food and water."""
    world = World()
    if fallback_food > 0:
        world.add_food(quantity=fallback_food)
    if fallback_water > 0:
        world.add_water(quantity=fallback_water)
    return world


def _build_default_species(world: World) -> List[Animal]:
    """Constructs default Chasseron species instance placed at world center."""
    center = (world.width / 2.0, world.height / 2.0)
    return [
        Animal(
            name="Chasseron",
            position=center,
            vision=80,
            smell_range=200,
            speed=10,
            diurnal=True,
            temperament="neutre",
            species_type="Chasseron",
        )
    ]


def _extract_position(world: World, *candidates: Any) -> Tuple[float, float]:
    """Extracts valid clamped position tuple from candidate objects."""
    for candidate in candidates:
        coords = _coerce_position(candidate)
        if coords is not None:
            return _clamp_position(coords, world)
    return _clamp_position((world.width / 2.0, world.height / 2.0), world)


def _extract_positions(world: World, value: Any) -> List[Tuple[float, float]]:
    """Extracts list of clamped position tuples from raw config value."""
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return []
    positions: List[Tuple[float, float]] = []
    for item in value:
        coords = _coerce_position(item)
        if coords is not None:
            positions.append(_clamp_position(coords, world))
    return positions


def _build_spawn_positions(
    world: World, anchor: Tuple[float, float], count: int
) -> List[Tuple[float, float]]:
    """Generates circular spawn position clusters around an anchor point."""
    if count <= 1:
        return [_clamp_position(anchor, world)]

    radius = max(18.0, min(float(world.width), float(world.height)) * 0.04)
    positions: List[Tuple[float, float]] = []
    for index in range(count):
        if index == 0:
            offset_x = 0.0
            offset_y = 0.0
        else:
            angle = random.uniform(0.0, 2.0 * 3.141592653589793)
            distance = random.uniform(radius * 0.25, radius)
            offset_x = math.cos(angle) * distance
            offset_y = math.sin(angle) * distance
        positions.append(
            _clamp_position(
                (anchor[0] + offset_x, anchor[1] + offset_y), world
            )
        )
    return positions


def _clamp_position(
    position: Tuple[float, float], world: World
) -> Tuple[float, float]:
    """Clamps position within world bounds and relocates off water."""
    x = max(0.0, min(float(world.width), float(position[0])))
    y = max(0.0, min(float(world.height), float(position[1])))
    if hasattr(world, "relocate_off_water"):
        return world.relocate_off_water(x, y)
    return (x, y)


def _coerce_position(value: Any) -> Optional[Tuple[float, float]]:
    """Coerces list/tuple/dict position specification to (x, y) tuple."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _safe_float_pair(value[0], value[1])
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return _safe_float_pair(value.get("x"), value.get("y"))
    return None


def _safe_float_pair(
    x_value: Any, y_value: Any
) -> Optional[Tuple[float, float]]:
    """Safe conversion of x and y raw inputs to float pair."""
    x = _coerce_float(x_value)
    y = _coerce_float(y_value)
    if x is None or y is None:
        return None
    return (x, y)


def _resolve_config_path(config_path: Optional[str]) -> Path:
    """Resolves relative or absolute path to a valid config file location."""
    if config_path is None:
        return DEFAULT_CONFIG_PATH

    candidate = Path(config_path)
    if candidate.is_absolute():
        return candidate.resolve()

    path_at_root = APP_ROOT / candidate
    if path_at_root.exists():
        return path_at_root.resolve()

    path_in_app = APP_ROOT / "app" / candidate
    if path_in_app.exists():
        return path_in_app.resolve()

    return path_at_root.resolve()


def _positive_int(value: Any) -> Optional[int]:
    """Coerces input value to a positive integer or None."""
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None
    return integer if integer > 0 else None


def _positive_float(value: Any) -> Optional[float]:
    """Coerces input value to a positive float or None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _coerce_float(value: Any) -> Optional[float]:
    """Coerces input value to float or None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> Optional[str]:
    """Coerces input value to stripped string or None."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _coerce_bool(value: Any) -> Optional[bool]:
    """Coerces input value to boolean representation or None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "oui"}:
            return True
        if lowered in {"false", "0", "no", "n", "non"}:
            return False
    return None


def _resolve_float_attr(
    key: str,
    entry: Dict[str, Any],
    default_chain: List[Dict[str, Any]],
    *,
    fallback: float,
) -> float:
    """Resolves float attribute value across inheritance chain."""
    value = _positive_float(entry.get(key))
    if value is not None:
        return value
    for defaults_source in default_chain:
        value = _positive_float(_extract_from_dict(defaults_source, key))
        if value is not None:
            return value
    return fallback


def _resolve_bool_attr(
    key: str,
    entry: Dict[str, Any],
    default_chain: List[Dict[str, Any]],
    *,
    fallback: bool,
) -> bool:
    """Resolves boolean attribute value across inheritance chain."""
    value = _coerce_bool(entry.get(key))
    if value is not None:
        return value
    for defaults_source in default_chain:
        value = _coerce_bool(_extract_from_dict(defaults_source, key))
        if value is not None:
            return value
    return fallback


def _resolve_str_from_chain(
    key: str, default_chain: List[Dict[str, Any]]
) -> Optional[str]:
    """Resolves string attribute value across inheritance chain."""
    for defaults_source in default_chain:
        value = _coerce_str(_extract_from_dict(defaults_source, key))
        if value:
            return value
    return None


def _resolve_traits(
    entry: Dict[str, Any], default_chain: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Merges traits dictionaries across inheritance chain."""
    merged: Dict[str, Any] = {}
    for defaults_source in reversed(default_chain):
        traits = _extract_traits(_extract_from_dict(defaults_source, "traits"))
        if traits:
            merged.update(traits)
    entry_traits = _extract_traits(entry.get("traits"))
    if entry_traits:
        merged.update(entry_traits)
    return merged


def _coerce_range(value: Any) -> Optional[Tuple[float, float]]:
    """Coerces range specification to positive (min, max) tuple."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        lower = _coerce_float(value[0])
        upper = _coerce_float(value[1])
    elif isinstance(value, dict):
        lower = _coerce_float(value.get("min"))
        upper = _coerce_float(value.get("max"))
    else:
        return None

    if lower is None or upper is None:
        return None
    if lower <= 0 or upper <= 0:
        return None
    return (min(lower, upper), max(lower, upper))


def _resolve_float_range_attr(
    key: str,
    entry: Dict[str, Any],
    default_chain: List[Dict[str, Any]],
) -> Optional[Tuple[float, float]]:
    """Resolves float range attribute value across inheritance chain."""
    range_key = f"{key}_range"
    resolved = _coerce_range(entry.get(range_key))
    if resolved is not None:
        return resolved

    for defaults_source in default_chain:
        resolved = _coerce_range(
            _extract_from_dict(defaults_source, range_key)
        )
        if resolved is not None:
            return resolved
    return None


def _extract_distribution(value: Any) -> Dict[str, int]:
    """Extracts food distribution dictionary mapping species to quantities."""
    if not isinstance(value, dict):
        return {}
    distribution: Dict[str, int] = {}
    for key, raw_count in value.items():
        count = _positive_int(raw_count)
        if count:
            distribution[str(key)] = count
    return distribution


def _extract_type_weights(value: Any) -> Dict[str, float]:
    """Extracts type weight dictionary mapping food classes to weights."""
    if not isinstance(value, dict):
        return {}
    weights: Dict[str, float] = {}
    for key, raw_weight in value.items():
        weight = _positive_float(raw_weight)
        if weight:
            weights[str(key)] = weight
    return weights


def _extract_traits(value: Any) -> Dict[str, Any]:
    """Extracts traits dictionary from arbitrary input."""
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items()}


def _extract_from_dict(container: Any, key: str) -> Any:
    """Safely extracts value from dictionary if container is a dict."""
    if isinstance(container, dict):
        return container.get(key)
    return None


def _load_species_preset(
    ref: Any, base_dir: Optional[Path]
) -> Optional[Dict[str, Any]]:
    """Loads species preset JSON file by path reference."""
    if isinstance(ref, dict):
        if "preset" in ref or "path" in ref or "file" in ref:
            ref = ref.get("preset") or ref.get("path") or ref.get("file")
        else:
            return ref

    path = _resolve_preset_path(ref, base_dir)
    if path is None:
        logger.warning("Species preset '%s' introuvable.", ref)
        return None

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        logger.warning("Impossible de lire le preset '%s': %s", path, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("JSON invalide pour le preset '%s': %s", path, exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Le preset '%s' doit contenir un objet JSON.", path)
        return None
    return data


def _resolve_preset_path(ref: Any, base_dir: Optional[Path]) -> Optional[Path]:
    """Resolves relative preset path across search directories."""
    if isinstance(ref, dict):
        ref = ref.get("preset") or ref.get("path") or ref.get("file")
    if not isinstance(ref, str) or not ref.strip():
        return None

    ref_path = Path(ref.strip())

    search_paths: List[Path] = []
    if ref_path.is_absolute():
        search_paths.append(ref_path)
    else:
        if base_dir is not None:
            search_paths.append(base_dir / ref_path)
        search_paths.append(SPECIES_PRESETS_DIR / ref_path)
        if ref_path.suffix == "":
            if base_dir is not None:
                search_paths.append((base_dir / ref_path).with_suffix(".json"))
            search_paths.append(
                (SPECIES_PRESETS_DIR / ref_path).with_suffix(".json")
            )

    seen: set[Path] = set()
    for path in search_paths:
        normalized = path.resolve() if path.is_absolute() else path
        if normalized in seen:
            continue
        seen.add(normalized)
        if path.exists():
            return path
    return None
