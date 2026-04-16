"""Helpers utilitaires pour finaliser les actions d'un individu."""
from __future__ import annotations

from typing import Any, Callable, Dict

LogFn = Callable[[str], None]


def resolve_consumption(world: Any, species: Any, log: LogFn) -> Dict[str, Any]:
    """Verifie si l'action en cours amene l'individu a consommer de la nourriture."""
    result = species.try_eat(world)
    if result and result.get("consumed", 0.0) > 0.0:
        log(f"{species.name} a mange {result['consumed']:.1f} calories.")
        return {"action_suffix": "_and_ate", "food_event": result}
    return {"action_suffix": "", "food_event": None}
