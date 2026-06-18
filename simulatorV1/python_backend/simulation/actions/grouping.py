"""Helpers de cohesion de groupe pour les especes sociales."""

from __future__ import annotations

from typing import Iterable, Tuple

from ..animal import Animal


def _compute_group_center(herd: Iterable[Animal]) -> Tuple[float, float]:
    members = list(herd)
    if not members:
        return 0.0, 0.0
    acc_x = sum(member.x for member in members)
    acc_y = sum(member.y for member in members)
    count = float(len(members))
    return acc_x / count, acc_y / count


def maintain_group_cohesion(
    animal: Animal,
    herd: Iterable[Animal],
    world,
    *,
    radius: float = 500.0,
    spacing: float = 120.0,
    alignment: float = 0.4,
    cohesion: float = 0.6,
) -> Tuple[bool, str]:
    """Maintient un groupe compact sans provoquer de superposition brutale."""

    def _attempt_move(
        target: dict[str, float], primary_action: str
    ) -> Tuple[bool, str]:
        if animal.move_towards(target, world):
            return True, primary_action
        if animal.random_move(world):
            return True, "herd_reposition"
        return False, ""

    herd_members = [
        member for member in herd if member is not animal and member.alive
    ]
    if not herd_members:
        return False, ""

    center_x, center_y = _compute_group_center([animal] + herd_members)
    center = {"x": center_x, "y": center_y}
    distance_to_center = animal.distance_to(center)

    # On recentre un individu qui s'ecarte trop du noyau du groupe.
    if distance_to_center > radius:
        return _attempt_move(center, "herd_return_to_center")

    # On evite ensuite que deux individus se collent de facon non naturelle.
    nearest = min(
        herd_members,
        key=lambda mate: animal.distance_to({"x": mate.x, "y": mate.y}),
    )
    separation = animal.distance_to({"x": nearest.x, "y": nearest.y})

    if separation < spacing * 0.6:
        avoidance_target = {
            "x": animal.x + (animal.x - nearest.x) * alignment,
            "y": animal.y + (animal.y - nearest.y) * alignment,
        }
        return _attempt_move(avoidance_target, "herd_avoid_collision")

    if distance_to_center > spacing:
        cohesion_target = {
            "x": animal.x + (center_x - animal.x) * cohesion,
            "y": animal.y + (center_y - animal.y) * cohesion,
        }
        return _attempt_move(cohesion_target, "herd_cohesion_step")

    return False, ""
