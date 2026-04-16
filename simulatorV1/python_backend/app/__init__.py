"""Expose les points d'entree applicatifs du simulateur sans importer `app.main` trop tot."""

from typing import Any

__all__ = ["run_cli"]


def run_cli(*args: Any, **kwargs: Any) -> Any:
    """Charge `app.main` a la demande pour eviter l'avertissement `runpy` avec `python -m`."""
    from .main import run_cli as _run_cli

    return _run_cli(*args, **kwargs)
