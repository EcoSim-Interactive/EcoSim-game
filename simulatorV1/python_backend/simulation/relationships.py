"""High-level dispatcher for social and inter-species behaviours."""
from __future__ import annotations

from typing import Iterable, Tuple

from .animal import Animal
from .ai import relationships as ai_relationships

__all__ = ["handle_species_relationships"]

# Backward compatibility wrapper.

def handle_species_relationships(
    animal: Animal,
    animals: Iterable[Animal],
    world,
    log,
) -> Tuple[bool, str, str, bool]:
    return ai_relationships.handle_species_relationships(animal, animals, world, log)
