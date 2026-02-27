"""Relationship-driven AI helpers."""
from __future__ import annotations

from typing import Iterable, Tuple

from ..animal import Animal
from ..actions import (
    enforce_territory,
    execute_predation_cycle,
    maintain_group_cohesion,
    seek_carcass_opportunity,
)


def handle_species_relationships(
    animal: Animal,
    animals: Iterable[Animal],
    world,
    log,
) -> Tuple[bool, str, str, bool]:
    """Apply relationship-driven behaviours before default survival rules."""
    traits = animal.get_traits()
    if not traits:
        return False, "", "", False

    territory_cfg = traits.get("territory")
    if isinstance(territory_cfg, dict):
        enforced, action = enforce_territory(animal, territory_cfg, world)
        if enforced:
            log(f"{animal.name} patrouille son territoire.")
            return True, action, "maintien du territoire", False

    if animal.pack_id or traits.get("role") in {"hunter", "leader", "patriarch"}:
        acted, action, resolve_food = execute_predation_cycle(animal, animals, world, log)
        if acted:
            motivation = "coordination de chasse" if "hunt" in action or "pride" in action else "partage de carcasse"
            return True, action, motivation, resolve_food

    if traits.get("scavenger"):
        acted, action, resolve_food = seek_carcass_opportunity(animal, world)
        if acted:
            return True, action, "charognage opportuniste", resolve_food

    herd_cfg = traits.get("herd_behavior")
    if isinstance(herd_cfg, dict):
        group_members = [
            member
            for member in animals
            if member is not animal
            and member.group_id
            and member.group_id == animal.group_id
            and member.alive
        ]
        if group_members:
            acted, action = maintain_group_cohesion(
                animal,
                [animal] + group_members,
                world,
                radius=float(herd_cfg.get("radius", 400.0)),
                spacing=float(herd_cfg.get("spacing", 120.0)),
                alignment=float(herd_cfg.get("alignment", 0.4)),
                cohesion=float(herd_cfg.get("cohesion", 0.5)),
            )
            if acted:
                return True, action, "dynamique de groupe", False

    return False, "", "", False
