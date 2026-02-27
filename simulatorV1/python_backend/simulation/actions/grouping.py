"""Group cohesion helpers for social species."""
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
    """Keep herd members within a soft radius and avoid collisions."""
    herd_members = [member for member in herd if member is not animal and member.alive]
    if not herd_members:
        return False, ""

    center_x, center_y = _compute_group_center([animal] + herd_members)
    center = {"x": center_x, "y": center_y}
    distance_to_center = animal.distance_to(center)

    # Pull toward herd center if drifting too far.
    if distance_to_center > radius:
        animal.move_towards(center, world)
        return True, "herd_return_to_center"

    # Maintain comfortable spacing with closest neighbour.
    nearest = min(herd_members, key=lambda mate: animal.distance_to({"x": mate.x, "y": mate.y}))
    separation = animal.distance_to({"x": nearest.x, "y": nearest.y})

    if separation < spacing * 0.6:
        avoidance_target = {
            "x": animal.x + (animal.x - nearest.x) * alignment,
            "y": animal.y + (animal.y - nearest.y) * alignment,
        }
        animal.move_towards(avoidance_target, world)
        return True, "herd_avoid_collision"

    if distance_to_center > spacing:
        cohesion_target = {
            "x": animal.x + (center_x - animal.x) * cohesion,
            "y": animal.y + (center_y - animal.y) * cohesion,
        }
        animal.move_towards(cohesion_target, world)
        return True, "herd_cohesion_step"

    return False, ""
