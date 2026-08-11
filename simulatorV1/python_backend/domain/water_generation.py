"""Procedural water source and river generation utilities."""

from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

_DIRECTIONS: Sequence[Tuple[int, int]] = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
)


def _rand_int_with_margin(bound: int, margin: float) -> int:
    """Returns random integer bounded within map limits with margin offset."""
    margin_int = int(max(0.0, margin))
    low = min(margin_int, max(0, bound))
    high = max(0, bound - margin_int)
    if high < low:
        low, high = 0, max(0, bound)
    return random.randint(low, high)


def generate_river_segments(
    width: int,
    height: int,
    length: int,
    *,
    max_attempts_multiplier: int = 10,
    key_point_step: int = 15,
) -> List[Dict[str, float]]:
    """Generates continuous river waypoint coordinates following global flow.

    Args:
        width (int): Grid width constraint.
        height (int): Grid height constraint.
        length (int): Target number of river segments.
        max_attempts_multiplier (int): Search attempt scaling multiplier.
        key_point_step (int): Distance step between river keypoints.

    Returns:
        List[Dict[str, float]]: List of point dicts with 'x' and 'y'.
    """
    if length <= 0:
        return []

    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)
    segments = [{"x": float(x), "y": float(y)}]

    flow_x = 1 if x < width / 2 else -1
    flow_y = 1 if y < height / 2 else -1

    if random.random() < 0.5:
        flow_y = 0
    elif random.random() < 0.5:
        flow_x = 0

    attempts = 0
    max_attempts = max(length * max_attempts_multiplier, 100)

    while len(segments) < length and attempts < max_attempts:
        attempts += 1
        candidates = []

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                score = (dx * flow_x) + (dy * flow_y)
                if score >= 0:
                    weight = 1 + (score * 2)
                    for _ in range(weight):
                        candidates.append((dx, dy))

        if not candidates:
            break

        move_dx, move_dy = random.choice(candidates)
        target_x = x + (move_dx * key_point_step)
        target_y = y + (move_dy * key_point_step)

        target_x = max(0, min(width - 1, target_x))
        target_y = max(0, min(height - 1, target_y))

        if int(target_x) == int(x) and int(target_y) == int(y):
            continue

        wobble = random.randint(-key_point_step // 3, key_point_step // 3)
        if move_dx == 0:
            target_x += wobble
        elif move_dy == 0:
            target_y += wobble

        target_x = max(0, min(width - 1, target_x))
        target_y = max(0, min(height - 1, target_y))

        x, y = target_x, target_y
        segments.append({"x": float(x), "y": float(y)})

    return segments


def trace_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Traces a line of discrete pixel coordinates using Bresenham's algorithm.

    Args:
        x1 (int): Starting x coordinate.
        y1 (int): Starting y coordinate.
        x2 (int): Ending x coordinate.
        y2 (int): Ending y coordinate.

    Returns:
        List[Tuple[int, int]]: List of rasterized (x, y) coordinate tuples.
    """
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy

    cx, cy = x1, y1

    while True:
        points.append((cx, cy))
        if cx == x2 and cy == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy

    return points


def generate_stagnant_pool_specs(
    width: int,
    height: int,
    count: int,
    capacity_range: Tuple[int, int],
    radius_range: Tuple[int, int] = (6, 18),
) -> List[Dict[str, float]]:
    """Generates stagnant water pool specifications with limited capacity.

    Args:
        width (int): Grid width.
        height (int): Grid height.
        count (int): Number of pools to place.
        capacity_range (Tuple[int, int]): Min and max capacity.
        radius_range (Tuple[int, int]): Min and max pool radius.

    Returns:
        List[Dict[str, float]]: Pool metadata dictionaries.
    """
    if count <= 0:
        return []

    low, high = sorted(capacity_range)
    low_radius, high_radius = sorted(radius_range)
    pools: List[Dict[str, float]] = []
    for _ in range(count):
        capacity = float(random.randint(low, high))
        radius = float(random.randint(low_radius, high_radius))
        pools.append(
            {
                "x": float(_rand_int_with_margin(width, radius)),
                "y": float(_rand_int_with_margin(height, radius)),
                "capacity": capacity,
                "max_capacity": capacity,
                "radius": radius,
            }
        )
    return pools


def generate_oasis_specs(
    width: int,
    height: int,
    count: int,
    capacity_range: Tuple[int, int],
    radius_range: Tuple[int, int],
) -> List[Dict[str, float]]:
    """Generates oasis water specifications with capacity and radius metadata.

    Args:
        width (int): Grid width.
        height (int): Grid height.
        count (int): Number of oases to generate.
        capacity_range (Tuple[int, int]): Min and max water capacity.
        radius_range (Tuple[int, int]): Min and max oasis radius.

    Returns:
        List[Dict[str, float]]: Oasis specifications dictionary list.
    """
    if count <= 0:
        return []

    low_cap, high_cap = sorted(capacity_range)
    low_radius, high_radius = sorted(radius_range)
    oasis: List[Dict[str, float]] = []
    for _ in range(count):
        capacity = float(random.randint(low_cap, high_cap))
        radius = float(random.randint(low_radius, high_radius))
        oasis.append(
            {
                "x": float(_rand_int_with_margin(width, radius)),
                "y": float(_rand_int_with_margin(height, radius)),
                "capacity": capacity,
                "max_capacity": capacity,
                "radius": radius,
            }
        )
    return oasis


def generate_lake_specs(
    width: int,
    height: int,
    count: int,
    capacity_range: Tuple[int, int],
    radius_range: Tuple[int, int],
    eccentricity_range: Tuple[float, float] = (0.7, 1.3),
) -> List[Dict[str, float]]:
    """Generates lake specifications with elliptical radii.

    Args:
        width (int): Grid width.
        height (int): Grid height.
        count (int): Number of lakes to generate.
        capacity_range (Tuple[int, int]): Min/max capacity tuple.
        radius_range (Tuple[int, int]): Min/max base radius tuple.
        eccentricity_range (Tuple[float, float]): Ellipse eccentricity range.

    Returns:
        List[Dict[str, float]]: Lake specification dictionaries.
    """
    if count <= 0:
        return []

    low_cap, high_cap = sorted(capacity_range)
    low_radius, high_radius = sorted(radius_range)
    low_ecc, high_ecc = sorted(eccentricity_range)

    lakes: List[Dict[str, float]] = []
    for _ in range(count):
        capacity = float(random.randint(low_cap, high_cap))
        base_radius = float(random.randint(low_radius, high_radius))
        ratio = random.uniform(low_ecc, high_ecc)
        radius_x = max(4.0, base_radius)
        radius_y = max(4.0, base_radius * ratio)
        margin = max(radius_x, radius_y)
        lakes.append(
            {
                "x": float(_rand_int_with_margin(width, margin)),
                "y": float(_rand_int_with_margin(height, margin)),
                "capacity": capacity,
                "max_capacity": capacity,
                "radius_x": radius_x,
                "radius_y": radius_y,
            }
        )
    return lakes


def _ordered_directions(
    prev_direction: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """Returns candidate directions favoring path continuity."""
    directions = list(_DIRECTIONS)
    random.shuffle(directions)
    ordered: List[Tuple[int, int]] = []

    if prev_direction in directions:
        ordered.append(prev_direction)
        directions.remove(prev_direction)

        gentle_turns = _gentle_turns(prev_direction)
        for turn in gentle_turns:
            if turn in directions:
                ordered.append(turn)
                directions.remove(turn)

    ordered.extend(directions)
    return ordered


def _gentle_turns(direction: Tuple[int, int]) -> Tuple[Tuple[int, int], ...]:
    """Computes adjacent direction vectors representing soft turns."""
    dx, dy = direction
    options: List[Tuple[int, int]] = []
    if dx != 0:
        options.append((dx, 0))
        options.append((dx, 1 if dy >= 0 else -1))
    if dy != 0:
        options.append((0, dy))
        options.append((1 if dx >= 0 else -1, dy))
    return tuple(
        opt for opt in options if opt in _DIRECTIONS and opt != (0, 0)
    )
