"""Compatibilite legacy: re-exporte l'API historique
via SpeciesCatalogStore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .species_catalog import SpeciesCatalogStore

_store = SpeciesCatalogStore(
    legacy_selection_file=Path(__file__).parent.resolve()
    / "species_selection.json"
)


def load_species_catalog() -> Dict[str, Any]:
    """Load the species catalog via the shared SpeciesCatalogStore."""
    return _store.load_catalog()


def build_selection_from_catalog(
    catalog: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build a selection from the catalog's default entries."""
    return _store.build_selection_from_catalog(catalog)


def load_species_selection(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load the saved species selection for the given catalog."""
    return _store.load_selection(catalog)


def save_species_selection(selection: List[Dict[str, Any]]) -> None:
    """Persist the given species selection to disk."""
    _store.save_selection(selection)


def sanitize_selection(
    raw_selection: List[Dict[str, Any]], catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Sanitize a raw selection against the given catalog."""
    return _store.sanitize_selection(raw_selection, catalog)


def selection_to_species_config(
    selection: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convert a selection into a ready-to-simulate species config."""
    return _store.selection_to_species_config(selection)
