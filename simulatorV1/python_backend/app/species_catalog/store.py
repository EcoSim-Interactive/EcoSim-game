"""Gestion orientee objet du catalogue d'especes et
de la selection utilisateur.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpeciesCatalogStore:
    """Encapsule le chargement/validation/persistance du catalogue
    d'especes.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        *,
        catalog_file: str = "catalog.json",
        selection_file: str = "selection.json",
        legacy_selection_file: Optional[Path] = None,
    ) -> None:
        self.base_dir = (base_dir or Path(__file__).parent).resolve()
        self.catalog_path = self.base_dir / catalog_file
        self.selection_path = self.base_dir / selection_file
        self.legacy_selection_path = legacy_selection_file

    @staticmethod
    def _deep_merge(
        base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = SpeciesCatalogStore._deep_merge(
                    merged[key], value
                )
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Impossible de lire %s: %s", path, exc)
            return None
        if not isinstance(payload, dict):
            logger.warning("Le fichier %s doit contenir un objet JSON.", path)
            return None
        return payload

    @staticmethod
    def _normalize_template(
        template: Dict[str, Any], profiles: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        inherits = template.get("inherits")
        profile_data: Dict[str, Any] = {}
        if isinstance(inherits, str) and inherits in profiles:
            profile_data = profiles[inherits]

        merged = SpeciesCatalogStore._deep_merge(profile_data, template)
        merged.pop("inherits", None)

        nutrition_range = merged.get("nutrition_range")
        if not isinstance(nutrition_range, dict):
            nutrition_range = {}
        min_value = nutrition_range.get("min")
        max_value = nutrition_range.get("max")
        try:
            min_float = float(min_value)
            max_float = float(max_value)
            if min_float > 0 and max_float > 0:
                merged["nutrition_range"] = {
                    "min": min(min_float, max_float),
                    "max": max(min_float, max_float),
                }
            else:
                merged["nutrition_range"] = {"min": 80.0, "max": 80.0}
        except (TypeError, ValueError):
            merged["nutrition_range"] = {"min": 80.0, "max": 80.0}

        return merged

    def load_catalog(self) -> Dict[str, Any]:
        payload = self._load_json(self.catalog_path) or {}
        profiles_raw = payload.get("profiles")
        templates_raw = payload.get("templates")

        profiles: Dict[str, Dict[str, Any]] = {}
        if isinstance(profiles_raw, dict):
            for key, value in profiles_raw.items():
                if isinstance(value, dict):
                    profiles[str(key)] = value

        templates: List[Dict[str, Any]] = []
        if isinstance(templates_raw, list):
            for entry in templates_raw:
                if isinstance(entry, dict):
                    normalized = self._normalize_template(entry, profiles)
                    template_id = normalized.get("id")
                    if isinstance(template_id, str) and template_id.strip():
                        normalized["id"] = template_id.strip()
                        templates.append(normalized)

        default_selection = payload.get("default_selection")
        if not isinstance(default_selection, list):
            default_selection = []

        return {
            "profiles": profiles,
            "templates": templates,
            "default_selection": default_selection,
        }

    def build_selection_from_catalog(
        self, catalog: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        templates = (
            catalog.get("templates") if isinstance(catalog, dict) else []
        )
        default_selection = (
            catalog.get("default_selection")
            if isinstance(catalog, dict)
            else []
        )
        if not isinstance(templates, list) or not isinstance(
            default_selection, list
        ):
            return []

        template_by_id: Dict[str, Dict[str, Any]] = {}
        for tpl in templates:
            if isinstance(tpl, dict):
                template_id = tpl.get("id")
                if isinstance(template_id, str) and template_id:
                    template_by_id[template_id] = tpl

        selection: List[Dict[str, Any]] = []
        for item in default_selection:
            if not isinstance(item, dict):
                continue
            template_id = item.get("template_id")
            if (
                not isinstance(template_id, str)
                or template_id not in template_by_id
            ):
                continue

            count = item.get("count", 0)
            try:
                count_int = max(0, int(count))
            except (TypeError, ValueError):
                count_int = 0
            if count_int <= 0:
                continue

            base = copy.deepcopy(template_by_id[template_id])
            base["template_id"] = template_id
            base["count"] = count_int
            selection.append(base)

        return selection

    def sanitize_selection(
        self, raw_selection: List[Dict[str, Any]], catalog: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        templates = (
            catalog.get("templates") if isinstance(catalog, dict) else []
        )
        template_by_id: Dict[str, Dict[str, Any]] = {}
        if isinstance(templates, list):
            for tpl in templates:
                if isinstance(tpl, dict) and isinstance(tpl.get("id"), str):
                    template_by_id[tpl["id"]] = tpl

        sanitized: List[Dict[str, Any]] = []
        for entry in raw_selection:
            if not isinstance(entry, dict):
                continue
            template_id = entry.get("template_id")
            if (
                not isinstance(template_id, str)
                or template_id not in template_by_id
            ):
                continue

            merged = self._deep_merge(template_by_id[template_id], entry)
            merged["template_id"] = template_id

            try:
                merged["count"] = max(0, int(merged.get("count", 0)))
            except (TypeError, ValueError):
                merged["count"] = 0
            if merged["count"] <= 0:
                continue

            for field in ("vision", "smell_range", "speed"):
                try:
                    merged[field] = float(
                        merged.get(
                            field, template_by_id[template_id].get(field, 0.0)
                        )
                    )
                except (TypeError, ValueError):
                    merged[field] = float(
                        template_by_id[template_id].get(field, 0.0)
                    )

            if "diurnal" in merged:
                merged["diurnal"] = bool(merged["diurnal"])

            if not isinstance(merged.get("temperament"), str):
                merged["temperament"] = str(
                    template_by_id[template_id].get("temperament", "neutre")
                )
            if not isinstance(merged.get("diet"), str):
                merged["diet"] = str(
                    template_by_id[template_id].get("diet", "omnivore")
                )

            nr = merged.get("nutrition_range")
            if not isinstance(nr, dict):
                nr = {}
            try:
                nr_min = float(nr.get("min", 80.0))
                nr_max = float(nr.get("max", 80.0))
            except (TypeError, ValueError):
                nr_min = 80.0
                nr_max = 80.0
            if nr_min <= 0 or nr_max <= 0:
                nr_min = 80.0
                nr_max = 80.0
            merged["nutrition_range"] = {
                "min": min(nr_min, nr_max),
                "max": max(nr_min, nr_max),
            }

            sanitized.append(merged)

        return sanitized

    def load_selection(self, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        payload = self._load_json(self.selection_path)
        if payload and isinstance(payload.get("selection"), list):
            return self.sanitize_selection(payload["selection"], catalog)

        if self.legacy_selection_path is not None:
            legacy_payload = self._load_json(self.legacy_selection_path)
            if legacy_payload and isinstance(
                legacy_payload.get("selection"), list
            ):
                sanitized = self.sanitize_selection(
                    legacy_payload["selection"], catalog
                )
                if sanitized:
                    self.save_selection(sanitized)
                    return sanitized

        return self.build_selection_from_catalog(catalog)

    def save_selection(self, selection: List[Dict[str, Any]]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.selection_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {"selection": selection}, handle, ensure_ascii=False, indent=2
            )

    @staticmethod
    def selection_to_species_config(
        selection: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        defaults = {
            "vision": 110,
            "smell_range": 220,
            "speed": 12,
            "diurnal": True,
            "temperament": "neutre",
            "position": [500, 500],
        }

        population: List[Dict[str, Any]] = []
        for entry in selection:
            if not isinstance(entry, dict):
                continue
            count = entry.get("count", 0)
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue
            if count_int <= 0:
                continue

            species_type = str(
                entry.get("species_type")
                or entry.get("id")
                or entry.get("template_id")
                or "species"
            )
            nutrition_range = (
                entry.get("nutrition_range")
                if isinstance(entry.get("nutrition_range"), dict)
                else {}
            )
            traits = (
                entry.get("traits")
                if isinstance(entry.get("traits"), dict)
                else {}
            )

            pop_entry: Dict[str, Any] = {
                "name": str(
                    entry.get("display_name")
                    or entry.get("name")
                    or species_type.title()
                ),
                "species_type": species_type,
                "count": count_int,
                "vision": float(entry.get("vision", defaults["vision"])),
                "smell_range": float(
                    entry.get("smell_range", defaults["smell_range"])
                ),
                "speed": float(entry.get("speed", defaults["speed"])),
                "diurnal": bool(entry.get("diurnal", defaults["diurnal"])),
                "temperament": str(
                    entry.get("temperament", defaults["temperament"])
                ),
                "diet": str(entry.get("diet", "omnivore")),
                "traits": copy.deepcopy(traits),
                "body_nutrition_range": {
                    "min": float(nutrition_range.get("min", 80.0)),
                    "max": float(nutrition_range.get("max", 80.0)),
                },
            }

            position = entry.get("position")
            if isinstance(position, (list, tuple)) and len(position) >= 2:
                try:
                    pop_entry["position"] = [
                        float(position[0]),
                        float(position[1]),
                    ]
                except (TypeError, ValueError):
                    pass

            positions = entry.get("positions")
            if isinstance(positions, list):
                normalized_positions: List[List[float]] = []
                for item in positions:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        try:
                            normalized_positions.append(
                                [float(item[0]), float(item[1])]
                            )
                        except (TypeError, ValueError):
                            continue
                if normalized_positions:
                    pop_entry["positions"] = normalized_positions
            population.append(pop_entry)

        return {
            "defaults": defaults,
            "population": population,
            "presets": [],
        }
