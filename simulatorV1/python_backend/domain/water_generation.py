"""Outils de generation procedurale des points d'eau et de leurs formes."""

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
    key_point_step: int = 15,  # Pas augmenté pour des courbes plus larges
) -> List[Dict[str, float]]:
    if length <= 0:
        return []

    # 1. Point de départ aléatoire
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)
    segments = [{"x": float(x), "y": float(y)}]

    # 2. DEFINIR LE FLUX GÉNÉRAL (L'astuce est ici)
    # On choisit une destination générale loin du point de départ
    # Par exemple, si on est à gauche (x < width/2), le flux va vers la droite
    # (+1)
    flow_x = 1 if x < width / 2 else -1
    flow_y = 1 if y < height / 2 else -1

    # On peut ajouter un peu d'aléatoire au flux pour qu'il ne soit pas parfaitement diagonal  # noqa: E501
    if random.random() < 0.5:
        flow_y = 0  # Flux principalement horizontal
    elif random.random() < 0.5:
        flow_x = 0  # Flux principalement vertical

    attempts = 0
    max_attempts = max(length * max_attempts_multiplier, 100)

    while len(segments) < length and attempts < max_attempts:
        attempts += 1

        # On va avancer de 'key_point_step' pixels
        # Mais on doit choisir un angle qui respecte le FLUX GÉNÉRAL

        # Liste des mouvements possibles (dx, dy) pour un segment
        # On favorise ceux qui vont dans le sens du flux
        candidates = []

        # On regarde les 8 directions possibles
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                # PRODUIT SCALAIRE : Si le mouvement va à l'opposé du flux
                # général, on l'ignore ou on le pénalise
                # Score > 0 : va dans le bon sens. Score < 0 : va en arrière (interdit)  # noqa: E501
                score = (dx * flow_x) + (dy * flow_y)

                if (
                    score >= 0
                ):  # On accepte seulement si ça ne recule pas par rapport au flux global  # noqa: E501
                    # On ajoute ce candidat (dx, dy) à la liste
                    # On l'ajoute plusieurs fois si le score est bon pour augmenter ses chances  # noqa: E501
                    weight = 1 + (
                        score * 2
                    )  # Poids: 1 (neutre) ou 3 (très bon sens)
                    for _ in range(weight):
                        candidates.append((dx, dy))

        if not candidates:
            break  # Coincé

        # Choix d'une direction parmi les candidats validés
        move_dx, move_dy = random.choice(candidates)

        # Calcul du point d'arrivée
        target_x = x + (move_dx * key_point_step)
        target_y = y + (move_dy * key_point_step)

        # Clamp aux limites
        target_x = max(0, min(width - 1, target_x))
        target_y = max(0, min(height - 1, target_y))

        # Si on n'a pas bougé (mur), on réessaie
        if int(target_x) == int(x) and int(target_y) == int(y):
            continue

        # Ajout d'une petite perturbation ("Wobble") pour que ce ne soit pas des lignes droites parfaites  # noqa: E501
        # On décale un peu le point d'arrivée perpendiculairement au mouvement
        wobble = random.randint(-key_point_step // 3, key_point_step // 3)
        if move_dx == 0:  # Mouvement vertical -> wobble horizontal
            target_x += wobble
        elif move_dy == 0:  # Mouvement horizontal -> wobble vertical
            target_y += wobble

        # Re-clamp après wobble
        target_x = max(0, min(width - 1, target_x))
        target_y = max(0, min(height - 1, target_y))

        x, y = target_x, target_y
        segments.append({"x": float(x), "y": float(y)})

    return segments


def trace_line(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Relie deux points par une ligne continue de pixels (Algorithme de Bresenham)."""  # noqa: E501
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
    """Return stagnant pool specifications with limited capacity."""
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
    """Return oasis specifications with limited capacity and radius metadata."""  # noqa: E501
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
    """Return lake specifications with ellipse-like radii."""
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
    """Return candidate directions favouring continuity."""
    directions = list(_DIRECTIONS)
    random.shuffle(directions)
    ordered: List[Tuple[int, int]] = []

    if prev_direction in directions:
        ordered.append(prev_direction)
        directions.remove(prev_direction)

        # favour gentle turns
        gentle_turns = _gentle_turns(prev_direction)
        for turn in gentle_turns:
            if turn in directions:
                ordered.append(turn)
                directions.remove(turn)

    ordered.extend(directions)
    return ordered


def _gentle_turns(direction: Tuple[int, int]) -> Tuple[Tuple[int, int], ...]:
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
