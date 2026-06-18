"""Helpers de persistance JSON pour les sorties de simulation."""

from __future__ import annotations

import copy
import json
import os
import re
from typing import Any, Dict, Iterable, Sequence

_RUN_SIMULATION = re.compile(r"simulation(\d+)\.json$")
_RUN_SUMMARY = re.compile(r"summary(\d+)\.json$")
_RUN_DIR = re.compile(r"log(\d+)$")
_SAFE_SLUG = re.compile(r"[^a-z0-9_-]+")


def ensure_logs_dir(logs_dir: str) -> None:
    """Cree le dossier de logs s'il n'existe pas encore."""

    if logs_dir:
        os.makedirs(logs_dir, exist_ok=True)


def _existing_run_indices(logs_dir: str) -> int:
    ensure_logs_dir(logs_dir)
    max_index = 0
    for name in os.listdir(logs_dir):
        path = os.path.join(logs_dir, name)
        if os.path.isdir(path):
            match_dir = _RUN_DIR.match(name)
            if match_dir:
                max_index = max(max_index, int(match_dir.group(1)))
            continue
        for pattern in (_RUN_SIMULATION, _RUN_SUMMARY):
            match = pattern.match(name)
            if match:
                max_index = max(max_index, int(match.group(1)))
    return max_index


def next_run_index(logs_dir: str) -> int:
    return _existing_run_indices(logs_dir) + 1


def _ensure_run_dir(logs_dir: str, index: int) -> str:
    ensure_logs_dir(logs_dir)
    run_dir = os.path.join(logs_dir, f"log{index}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def _slugify(value: str | None, *, default: str = "entity") -> str:
    if not value:
        value = default
    value = value.strip().lower().replace(" ", "_")
    value = _SAFE_SLUG.sub("-", value)
    return value or default


def write_step(
    logs_dir: str, step_number: int, step_data: Dict[str, Any]
) -> str:
    ensure_logs_dir(logs_dir)
    filename = os.path.join(logs_dir, f"step{step_number + 1}.json")
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(step_data, handle, indent=2)
    return filename


def write_summary(
    logs_dir: str,
    summary_data: Dict[str, Any],
    *,
    index: int | None = None,
    filename: str | None = None,
) -> str:
    ensure_logs_dir(logs_dir)
    if index is None:
        index = next_run_index(logs_dir)
    run_dir = _ensure_run_dir(logs_dir, index)
    target = filename or "summary.json"
    path = os.path.join(run_dir, target)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(summary_data, handle, indent=2)
    return path


def _compact_steps(
    steps: Sequence[Dict[str, Any]],
) -> Iterable[Dict[str, Any]]:
    """Reduce step payloads to the fields utiles au rerun/affichage Godot."""
    for step in steps:
        if not isinstance(step, dict):
            continue
        compact_step: Dict[str, Any] = {
            "step": step.get("step"),
            "hour": step.get("hour"),
            "minute": step.get("minute"),
            "is_day": step.get("is_day"),
            "time_label": step.get("time_label"),
            "new_food_sources": step.get("new_food_sources", []),
            "updated_food_sources": step.get("updated_food_sources", []),
            "removed_food_ids": step.get("removed_food_ids", []),
        }
        species_states: list[Dict[str, Any]] = []
        for status in step.get("species", []):
            if not isinstance(status, dict):
                continue
            after = status.get("after") or {}
            before = status.get("before") or {}
            x = after.get("x", before.get("x"))
            y = after.get("y", before.get("y"))
            species_states.append(
                {
                    "name": status.get("display_name") or status.get("name"),
                    "species_type": status.get("species_type"),
                    "diet": status.get("diet"),
                    "after": {
                        "x": x if x is not None else 0.0,
                        "y": y if y is not None else 0.0,
                        "alive": after.get("alive", True),
                    },
                }
            )
        compact_step["species"] = species_states
        yield compact_step


def write_steps_bundle(
    logs_dir: str,
    steps_data: Sequence[Dict[str, Any]],
    *,
    summary_data: Dict[str, Any] | None = None,
    world_data: Dict[str, Any] | None = None,
    duration_sec: float | None = None,
    index: int | None = None,
    filename: str | None = None,
    compact: bool = True,
) -> str:
    """Persist all computed steps into a single JSON file.

    When ``summary_data`` is provided, it is appended under the
    ``summary`` key so the consumer can access the resume without
    opening another file.
    """

    ensure_logs_dir(logs_dir)
    if index is None:
        index = next_run_index(logs_dir)
    run_dir = _ensure_run_dir(logs_dir, index)
    if filename is None:
        filename = "simulation.json"

    path = os.path.join(run_dir, filename)
    payload: Dict[str, Any] = {}
    payload["steps"] = list(
        _compact_steps(steps_data) if compact else steps_data
    )
    if summary_data is not None:
        payload["summary"] = summary_data
    if world_data is not None:
        payload["world"] = world_data
    if duration_sec is not None:
        payload["generation_duration_sec"] = duration_sec

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def _serialize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    serialized: Dict[str, Any] = {}
    for key, value in meta.items():
        if isinstance(value, set):
            serialized[key] = sorted(value)
        else:
            serialized[key] = value
    return serialized


def _compact_registry_entries(
    entries: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Produit un resume leger pour les vues derivees groupe/espece/regime."""
    action_counts: Dict[str, int] = {}
    total_entries = 0
    alive_entries = 0
    dead_entries = 0
    first_step = None
    last_step = None
    last_entry = None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        total_entries += 1
        step = entry.get("step")
        if first_step is None:
            first_step = step
        last_step = step
        last_entry = entry
        action = str(entry.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        after = entry.get("after") or {}
        if after.get("alive", True):
            alive_entries += 1
        else:
            dead_entries += 1

    return {
        "entry_count": total_entries,
        "first_step": first_step,
        "last_step": last_step,
        "alive_entries": alive_entries,
        "dead_entries": dead_entries,
        "action_counts": action_counts,
        "last_entry": last_entry,
    }


def _collect_members(
    meta: Dict[str, Any], summary_lookup: Dict[str, Any]
) -> Iterable[Dict[str, Any]]:
    identifiers = meta.get("member_ids")
    collected: list[Dict[str, Any]] = []
    if isinstance(identifiers, Iterable) and not isinstance(
        identifiers, (str, bytes)
    ):
        for identifier in sorted(
            {
                str(item)
                for item in identifiers
                if isinstance(item, (str, int, str))
            }
        ):
            summary = summary_lookup.get(identifier)
            if summary:
                collected.append(summary)
        if collected:
            return collected

    members = meta.get("members")
    if isinstance(members, Iterable) and not isinstance(members, (str, bytes)):
        for name in sorted(
            {
                str(item)
                for item in members
                if isinstance(item, (str, int, str))
            }
        ):
            summary = summary_lookup.get(name)
            if summary:
                collected.append(summary)
    return collected


def write_entity_logs(
    logs_dir: str,
    steps_data: Sequence[Dict[str, Any]],
    *,
    index: int,
    summary_data: Dict[str, Any] | None = None,
) -> None:
    run_dir = _ensure_run_dir(logs_dir, index)
    animals_dir = os.path.join(run_dir, "animals")
    groups_dir = os.path.join(run_dir, "groups")
    species_dir = os.path.join(run_dir, "species")
    diets_dir = os.path.join(run_dir, "diets")

    os.makedirs(animals_dir, exist_ok=True)
    os.makedirs(groups_dir, exist_ok=True)
    os.makedirs(species_dir, exist_ok=True)
    os.makedirs(diets_dir, exist_ok=True)

    animals: Dict[str, Dict[str, Any]] = {}
    groups: Dict[str, Dict[str, Any]] = {}
    species_map: Dict[str, Dict[str, Any]] = {}
    diets: Dict[str, Dict[str, Any]] = {}
    dead_animals: set[str] = set()

    summary_lookup: Dict[str, Any] = {}
    if summary_data:
        for entry in summary_data.get("species", []):
            if not isinstance(entry, dict):
                continue
            keys: list[str] = []
            identifier = entry.get("animal_id")
            if identifier is not None:
                keys.append(str(identifier))
            original = entry.get("original_name")
            if original:
                keys.append(str(original))
            name_key = entry.get("name")
            if name_key:
                keys.append(str(name_key))
            for key in keys:
                summary_lookup[key] = entry

    for step in steps_data:
        step_info = {
            "step": step.get("step"),
            "time": {
                "hour": step.get("hour"),
                "minute": step.get("minute"),
                "is_day": step.get("is_day"),
                "label": step.get("time_label"),
            },
        }

        for status in step.get("species", []):
            if not isinstance(status, dict):
                continue

            name = status.get("name") or "Inconnu"
            animal_id = status.get("animal_id")
            species_type = status.get("species_type") or "unknown"
            diet = status.get("diet") or "unknown"
            group_id = status.get("group_id")
            pack_id = status.get("pack_id")
            after_state = status.get("after") or {}

            entry = {
                "step": step_info["step"],
                "time": dict(step_info["time"]),
                "action": status.get("action"),
                "motivation": status.get("motivation"),
                "before": status.get("before"),
                "after": status.get("after"),
                "food_event": status.get("food_event"),
            }

            identifier = animal_id if animal_id is not None else name
            animal_key = str(identifier)
            if animal_key in dead_animals:
                continue
            animal_bucket = animals.setdefault(
                animal_key,
                {
                    "meta": {
                        "name": name,
                        "display_name": status.get("display_name", name),
                        "animal_id": animal_id,
                        "species_type": species_type,
                        "diet": diet,
                        "group_id": group_id,
                        "pack_id": pack_id,
                        "sex": status.get("sex"),
                        "age_stage": status.get("age_stage"),
                        "age_years": status.get("age_years"),
                        "original_name": status.get("original_name"),
                        "traits": copy.deepcopy(status.get("traits", {})),
                        "alive": after_state.get("alive", True),
                    },
                    "entries": [],
                },
            )
            animal_bucket["entries"].append(entry)
            meta = animal_bucket["meta"]
            if after_state:
                meta["age_years"] = after_state.get(
                    "age_years", meta.get("age_years")
                )
                meta["age_stage"] = after_state.get(
                    "age_stage", meta.get("age_stage")
                )
                meta["display_name"] = after_state.get(
                    "display_name", meta.get("display_name", meta.get("name"))
                )
                meta["name"] = meta.get("display_name", meta.get("name"))
            meta["sex"] = status.get("sex", meta.get("sex"))
            meta["original_name"] = status.get(
                "original_name", meta.get("original_name")
            )
            meta["traits"] = copy.deepcopy(
                status.get("traits", meta.get("traits", {}))
            )
            meta["alive"] = after_state.get("alive", meta.get("alive", True))
            if not meta.get("alive", True):
                meta["death_step"] = step_info["step"]
                dead_animals.add(animal_key)

            if group_id:
                group_bucket = groups.setdefault(
                    str(group_id),
                    {
                        "meta": {
                            "group_id": group_id,
                            "members": set(),
                            "member_ids": set(),
                            "species_types": set(),
                            "sexes": set(),
                        },
                        "entries": [],
                    },
                )
                group_bucket["meta"]["members"].add(name)
                group_bucket["meta"]["member_ids"].add(animal_key)
                group_bucket["meta"]["species_types"].add(species_type)
                if status.get("sex"):
                    group_bucket["meta"]["sexes"].add(status.get("sex"))
                group_bucket["entries"].append(entry)

            species_bucket = species_map.setdefault(
                str(species_type),
                {
                    "meta": {
                        "species_type": species_type,
                        "diet": diet,
                        "members": set(),
                        "member_ids": set(),
                        "sexes": set(),
                    },
                    "entries": [],
                },
            )
            species_bucket["meta"]["members"].add(name)
            species_bucket["meta"]["member_ids"].add(animal_key)
            if status.get("sex"):
                species_bucket["meta"]["sexes"].add(status.get("sex"))
            species_bucket["entries"].append(entry)

            diet_bucket = diets.setdefault(
                str(diet),
                {
                    "meta": {
                        "diet": diet,
                        "species_types": set(),
                        "members": set(),
                        "member_ids": set(),
                        "sexes": set(),
                    },
                    "entries": [],
                },
            )
            diet_bucket["meta"]["species_types"].add(species_type)
            diet_bucket["meta"]["members"].add(name)
            diet_bucket["meta"]["member_ids"].add(animal_key)
            if status.get("sex"):
                diet_bucket["meta"]["sexes"].add(status.get("sex"))
            diet_bucket["entries"].append(entry)

    def _write_registry(
        directory: str,
        registry: Dict[str, Dict[str, Any]],
        *,
        include_entries: bool,
    ) -> None:
        used_slugs: set[str] = set()
        for key, payload in registry.items():
            meta = _serialize_meta(payload.get("meta", {}))
            entries = payload.get("entries", [])
            data: Dict[str, Any] = {"meta": meta}
            if include_entries:
                data["entries"] = entries
            else:
                data["stats"] = _compact_registry_entries(entries)
            summary = None
            if meta.get("animal_id") is not None:
                summary = summary_lookup.get(str(meta["animal_id"]))
            if summary is None and meta.get("original_name"):
                summary = summary_lookup.get(str(meta["original_name"]))
            if summary is None and meta.get("name"):
                summary = summary_lookup.get(str(meta["name"]))
            if summary:
                data["summary"] = summary
            members_snapshot = list(
                _collect_members(payload.get("meta", {}), summary_lookup)
            )
            if members_snapshot:
                data["members_summary"] = members_snapshot
                data_meta_members = [
                    member.get("display_name") or member.get("name")
                    for member in members_snapshot
                    if isinstance(member, dict)
                ]
                if data_meta_members:
                    data["meta"]["members"] = data_meta_members
            label = (
                meta.get("name")
                or meta.get("group_id")
                or meta.get("species_type")
                or meta.get("diet")
                or key
            )
            slug_base = _slugify(str(label))
            slug = slug_base
            if slug in used_slugs:
                suffix = _slugify(str(key))
                slug = f"{slug_base}-{suffix}" if suffix else slug_base
            counter = 2
            while slug in used_slugs:
                slug = f"{slug_base}-{counter}"
                counter += 1
            used_slugs.add(slug)
            filename = os.path.join(directory, f"{slug}.json")
            with open(filename, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

    _write_registry(animals_dir, animals, include_entries=True)
    _write_registry(groups_dir, groups, include_entries=False)
    _write_registry(species_dir, species_map, include_entries=False)
    _write_registry(diets_dir, diets, include_entries=False)
