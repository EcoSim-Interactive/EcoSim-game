"""Domain entity representing the world hosting the species."""
from __future__ import annotations

from .constants import (
    DAY_END_HOUR,
    DAY_START_HOUR,
    DEFAULT_CARCASS_NUTRITION,
    DEFAULT_FOOD_NUTRITION,
    DEFAULT_MINUTES_PER_STEP,
    DRINK_TARGET_SEARCH_RADIUS,
    DEFAULT_WATER_DEPTH,
    DEFAULT_WATER_DEPTH_BY_TYPE,
    RELOCATE_OFF_WATER_ATTEMPTS,
    RELOCATE_OFF_WATER_RADIUS,
    RELOCATE_OFF_WATER_FALLBACK_ATTEMPTS,
    RELOCATE_OFF_WATER_FALLBACK_RADIUS,
)

from typing import Any, Dict, List, Optional, Tuple
import math
import random

from .food_generation import DEFAULT_FOOD_PROFILES, generate_food_sources, resolve_food_profile
from .water_generation import (
    generate_lake_specs,
    generate_oasis_specs,
    generate_river_segments,
    generate_stagnant_pool_specs,
    trace_line,
)


class World:
    def __init__(self, width: int = 1000, height: int = 1000, minutes_per_step: int = DEFAULT_MINUTES_PER_STEP) -> None:
        self.width = width
        self.height = height
        self.minutes_per_step = minutes_per_step
        self.food_sources: List[Dict[str, Any]] = []
        self.water_sources: List[Dict[str, Any]] = []
        self.terrain: list[int[str]] = []
        self._food_id_seq = 0
        self._water_id_seq = 0
        self._water_body_seq = 0
        self._water_bodies: Dict[str, Dict[str, float]] = {}
        self._water_tiles: set = set()
        self._water_tile_lookup: Dict[tuple, Dict[str, Any]] = {}
        self._water_tile_depth: Dict[tuple, float] = {}
        self._water_depth_by_type = dict(DEFAULT_WATER_DEPTH_BY_TYPE)

    # ------------------------------------------------------------------
    # Food generation helpers

    def add_food(
        self,
        quantity: int = 10,
        *,
        distribution: Optional[Dict[str, int]] = None,
        type_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """Populate the world with randomly placed food sources of various vegetal types."""
        specs = generate_food_sources(
            self.width,
            self.height,
            quantity,
            distribution=distribution,
            type_weights=type_weights,
            profiles=DEFAULT_FOOD_PROFILES,
        )
        for spec in specs:
            position = self._relocate_off_water(spec["x"], spec["y"])
            if position is None:
                continue
            self._register_food_source(
                position[0],
                position[1],
                food_type=spec["type"],
                nutrition=spec.get("nutrition"),
                metadata=spec.get("metadata"),
                food_class=spec.get("food_class", "plant"),
            )

    def add_food_placements(self, placements: List[Dict[str, Any]]) -> None:
        """Add explicit food positions defined in configuration files."""
        for placement in placements or []:
            if not isinstance(placement, dict):
                continue
            x = placement.get("x")
            y = placement.get("y")
            if x is None or y is None:
                continue
            raw_type = placement.get("type")
            food_type, profile = resolve_food_profile(raw_type, DEFAULT_FOOD_PROFILES)
            nutrition_override = self._to_optional_float(placement.get("nutrition"))
            metadata = placement.get("metadata")
            if not isinstance(metadata, dict):
                default_metadata = profile.get("metadata")
                metadata = dict(default_metadata) if isinstance(default_metadata, dict) else None
            else:
                metadata = dict(metadata)
            position = self._relocate_off_water(x, y)
            if position is None:
                continue
            self._register_food_source(
                position[0],
                position[1],
                food_type=food_type,
                nutrition=nutrition_override if nutrition_override is not None else profile.get("nutrition"),
                metadata=metadata,
                food_class=placement.get("food_class", "plant"),
            )

    # ------------------------------------------------------------------
    # Water generation helpers

    def add_water(
        self,
        quantity: int = 5,
        *,
        river_segments: Optional[int] = None,
        stagnant_count: Optional[int] = None,
        oasis_count: Optional[int] = None,
        lake_count: Optional[int] = None,
        fill_step: Optional[int] = None,
    ) -> None:
        """Populate the world with a mix of rivers, lakes, pools, and oasis."""
        if quantity <= 0:
            return

        fill_step = max(1, int(fill_step or 1))
        river_segments = river_segments if river_segments is not None else max(3, quantity)
        stagnant_count = stagnant_count if stagnant_count is not None else max(1, quantity // 3)
        oasis_count = oasis_count if oasis_count is not None else max(1, quantity // 4)
        lake_count = lake_count if lake_count is not None else max(1, quantity // 5)

        self.add_river(length=river_segments)
        self.add_stagnant_pools(count=stagnant_count, fill_step=fill_step)
        self.add_oasis(count=oasis_count, fill_step=fill_step)
        self.add_lakes(count=lake_count, fill_step=fill_step)

    def add_river(self, length: int = 8, *, max_step: int = 60) -> None:
            if length <= 0:
                return

            river_label = f"river_{self._water_id_seq + 1}"
            
            # 1. Générer les points clés (éloignés les uns des autres)
            key_segments = generate_river_segments(
                self.width,
                self.height,
                length,
                key_point_step=15,
            )
            
            if not key_segments:
                return

            # 2. RELIER LES POINTS (Interpolation)
            # On crée un chemin continu pixel par pixel entre les points clés
            full_path_coords = []
            for i in range(len(key_segments) - 1):
                p1 = key_segments[i]
                p2 = key_segments[i+1]
                
                # C'est ici que la magie opère : on remplit le vide
                segment_pixels = trace_line(
                    int(p1["x"]), int(p1["y"]), 
                    int(p2["x"]), int(p2["y"])
                )
                full_path_coords.extend(segment_pixels)

            # On nettoie les doublons potentiels tout en gardant l'ordre (si possible) ou set simple
            # Pour une rivière, l'ordre compte pour la largeur, donc on fait attention
            unique_path = []
            seen = set()
            for p in full_path_coords:
                if p not in seen:
                    seen.add(p)
                    unique_path.append(p)

            # 3. Élargissement progressif
            MIN_WIDTH = 4
            MAX_WIDTH = 28
            total_len = len(unique_path)
            registered = set()

            for i, (cx, cy) in enumerate(unique_path):
                # Progression de 0.0 à 1.0 le long de la rivière
                progress = i / max(1, total_len)
                
                # Largeur variable
                current_width = MIN_WIDTH + (MAX_WIDTH - MIN_WIDTH) * progress
                radius = max(1, int(current_width / 2))

                # Dessiner le cercle/carré d'eau autour du point
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        # Astuce: (dx*dx + dy*dy) <= radius*radius fait un cercle au lieu d'un carré
                        # mais un carré est plus simple et suffit souvent.
                        nx, ny = cx + dx, cy + dy
                        
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if (nx, ny) in registered:
                                continue
                            registered.add((nx, ny))
                            self._register_water_source(
                                nx, ny,
                                water_type="river",
                                capacity=None,
                                max_capacity=None,
                                metadata={"river_id": river_label}
                            )

    def add_stagnant_pools(
        self,
        count: int = 3,
        *,
        capacity_range: Tuple[int, int] = (50, 120),
        radius_range: Tuple[int, int] = (4, 10),
        fill_step: int = 1,
    ) -> None:
        """Create isolated stagnant water points with limited capacity."""
        specs = generate_stagnant_pool_specs(self.width, self.height, count, capacity_range, radius_range)
        for spec in specs:
            center_x = int(round(spec["x"]))
            center_y = int(round(spec["y"]))
            radius = int(round(spec.get("radius") or 0))
            if radius <= 0:
                continue
            body_id = self._create_water_body(spec["capacity"], spec["max_capacity"])
            fill_step = max(1, int(fill_step))

            blob_count = random.randint(3, 6)
            carve_count = random.randint(1, 3)
            blobs = []
            carves = []
            max_r = radius

            for _ in range(blob_count):
                offset_x = int(round(random.uniform(-0.4, 0.4) * radius))
                offset_y = int(round(random.uniform(-0.4, 0.4) * radius))
                blob_r = max(3, int(round(radius * random.uniform(0.25, 0.6))))
                blobs.append((offset_x, offset_y, blob_r))
                max_r = max(max_r, abs(offset_x) + blob_r, abs(offset_y) + blob_r)

            for _ in range(carve_count):
                offset_x = int(round(random.uniform(-0.35, 0.35) * radius))
                offset_y = int(round(random.uniform(-0.35, 0.35) * radius))
                carve_r = max(2, int(round(radius * random.uniform(0.15, 0.3))))
                carves.append((offset_x, offset_y, carve_r))

            r_sq = float(radius * radius)
            inv_r_sq = 1.0 / r_sq
            edge_start = 0.8
            edge_noise = 0.5
            edge_hole_chance = 0.18

            for dx in range(-max_r, max_r + 1, fill_step):
                for dy in range(-max_r, max_r + 1, fill_step):
                    inside = False
                    min_value = None
                    value = (dx * dx + dy * dy) * inv_r_sq
                    if value <= 1.0:
                        inside = True
                        min_value = value
                    for off_x, off_y, blob_r in blobs:
                        bx = dx - off_x
                        by = dy - off_y
                        br_sq = float(blob_r * blob_r)
                        value = (bx * bx + by * by) / br_sq
                        if value <= 1.0:
                            inside = True
                            min_value = value if min_value is None else min(min_value, value)
                    if inside and carves:
                        for off_x, off_y, carve_r in carves:
                            bx = dx - off_x
                            by = dy - off_y
                            cr_sq = float(carve_r * carve_r)
                            value = (bx * bx + by * by) / cr_sq
                            if value <= 1.0:
                                inside = False
                                break
                    if not inside:
                        continue
                    if min_value is not None and min_value > edge_start:
                        threshold = 1.0 + (random.random() - 0.5) * edge_noise
                        if min_value > threshold:
                            continue
                        if min_value > 0.9 and random.random() < edge_hole_chance:
                            continue

                    nx, ny = center_x + dx, center_y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        self._register_water_source(
                            nx,
                            ny,
                            water_type="stagnant",
                            capacity=None,
                            max_capacity=None,
                            metadata=None,
                            body_id=body_id,
                        )

    def add_oasis(
        self,
        count: int = 2,
        *,
        capacity_range: Tuple[int, int] = (100, 220),
        radius_range: Tuple[int, int] = (10, 26),
        fill_step: int = 1,
    ) -> None:
        """Create oasis water points with limited but higher capacities."""
        specs = generate_oasis_specs(self.width, self.height, count, capacity_range, radius_range)
        for spec in specs:
            center_x = int(round(spec["x"]))
            center_y = int(round(spec["y"]))
            radius = int(round(spec.get("radius") or 0))
            if radius <= 0:
                continue
            body_id = self._create_water_body(spec["capacity"], spec["max_capacity"])
            fill_step = max(1, int(fill_step))

            blob_count = random.randint(4, 8)
            carve_count = random.randint(1, 3)
            blobs = []
            carves = []
            max_r = radius

            for _ in range(blob_count):
                offset_x = int(round(random.uniform(-0.45, 0.45) * radius))
                offset_y = int(round(random.uniform(-0.45, 0.45) * radius))
                blob_r = max(3, int(round(radius * random.uniform(0.25, 0.65))))
                blobs.append((offset_x, offset_y, blob_r))
                max_r = max(max_r, abs(offset_x) + blob_r, abs(offset_y) + blob_r)

            for _ in range(carve_count):
                offset_x = int(round(random.uniform(-0.35, 0.35) * radius))
                offset_y = int(round(random.uniform(-0.35, 0.35) * radius))
                carve_r = max(2, int(round(radius * random.uniform(0.12, 0.28))))
                carves.append((offset_x, offset_y, carve_r))

            r_sq = float(radius * radius)
            inv_r_sq = 1.0 / r_sq
            edge_start = 0.78
            edge_noise = 0.5
            edge_hole_chance = 0.18

            for dx in range(-max_r, max_r + 1, fill_step):
                for dy in range(-max_r, max_r + 1, fill_step):
                    inside = False
                    min_value = None
                    value = (dx * dx + dy * dy) * inv_r_sq
                    if value <= 1.0:
                        inside = True
                        min_value = value
                    for off_x, off_y, blob_r in blobs:
                        bx = dx - off_x
                        by = dy - off_y
                        br_sq = float(blob_r * blob_r)
                        value = (bx * bx + by * by) / br_sq
                        if value <= 1.0:
                            inside = True
                            min_value = value if min_value is None else min(min_value, value)
                    if inside and carves:
                        for off_x, off_y, carve_r in carves:
                            bx = dx - off_x
                            by = dy - off_y
                            cr_sq = float(carve_r * carve_r)
                            value = (bx * bx + by * by) / cr_sq
                            if value <= 1.0:
                                inside = False
                                break
                    if not inside:
                        continue
                    if min_value is not None and min_value > edge_start:
                        threshold = 1.0 + (random.random() - 0.5) * edge_noise
                        if min_value > threshold:
                            continue
                        if min_value > 0.9 and random.random() < edge_hole_chance:
                            continue

                    nx, ny = center_x + dx, center_y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        self._register_water_source(
                            nx,
                            ny,
                            water_type="oasis",
                            capacity=None,
                            max_capacity=None,
                            metadata=None,
                            body_id=body_id,
                        )

    def add_lakes(
        self,
        count: int = 1,
        *,
        capacity_range: Tuple[int, int] = (400, 1100),
        radius_range: Tuple[int, int] = (24, 60),
        eccentricity_range: Tuple[float, float] = (0.6, 1.5),
        fill_step: int = 1,
    ) -> None:
        """Create lake water bodies with irregular outlines."""
        specs = generate_lake_specs(
            self.width,
            self.height,
            count,
            capacity_range,
            radius_range,
            eccentricity_range,
        )
        for spec in specs:
            center_x = int(round(spec["x"]))
            center_y = int(round(spec["y"]))
            radius_x = int(round(spec.get("radius_x") or 0))
            radius_y = int(round(spec.get("radius_y") or 0))
            if radius_x <= 0 or radius_y <= 0:
                self._register_water_source(
                    center_x,
                    center_y,
                    water_type="lake",
                    capacity=spec["capacity"],
                    max_capacity=spec["max_capacity"],
                    metadata=None,
                )
                continue

            blob_count = random.randint(6, 12)
            blobs = []
            carve_count = random.randint(2, 5)
            carves = []
            arm_count = random.randint(2, 5)
            arms = []
            max_rx = radius_x
            max_ry = radius_y

            for _ in range(blob_count):
                offset_x = int(round(random.uniform(-0.5, 0.5) * radius_x))
                offset_y = int(round(random.uniform(-0.5, 0.5) * radius_y))
                blob_rx = max(4, int(round(radius_x * random.uniform(0.2, 0.7))))
                blob_ry = max(4, int(round(radius_y * random.uniform(0.2, 0.7))))
                blobs.append((offset_x, offset_y, blob_rx, blob_ry))
                max_rx = max(max_rx, abs(offset_x) + blob_rx)
                max_ry = max(max_ry, abs(offset_y) + blob_ry)

            for _ in range(carve_count):
                offset_x = int(round(random.uniform(-0.45, 0.45) * radius_x))
                offset_y = int(round(random.uniform(-0.45, 0.45) * radius_y))
                carve_rx = max(3, int(round(radius_x * random.uniform(0.12, 0.3))))
                carve_ry = max(3, int(round(radius_y * random.uniform(0.12, 0.3))))
                carves.append((offset_x, offset_y, carve_rx, carve_ry))

            for _ in range(arm_count):
                angle = random.uniform(0.0, 2.0 * math.pi)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                arm_len = max(6.0, radius_x * random.uniform(0.6, 1.4))
                arm_w = max(3.0, radius_y * random.uniform(0.08, 0.2))
                offset = arm_len * random.uniform(0.25, 0.6)
                arms.append((cos_a, sin_a, arm_len, arm_w, offset))
                max_rx = max(max_rx, int(abs(offset) + arm_len))
                max_ry = max(max_ry, int(arm_w * 1.5))

            body_id = self._create_water_body(spec["capacity"], spec["max_capacity"])
            fill_step = max(1, int(fill_step))
            rx_sq = float(radius_x * radius_x)
            ry_sq = float(radius_y * radius_y)
            inv_rx_sq = 1.0 / rx_sq
            inv_ry_sq = 1.0 / ry_sq
            edge_start = 0.78
            edge_noise = 0.55
            edge_hole_chance = 0.2

            for dx in range(-max_rx, max_rx + 1, fill_step):
                for dy in range(-max_ry, max_ry + 1, fill_step):
                    inside = False
                    min_value = None
                    value = (dx * dx) * inv_rx_sq + (dy * dy) * inv_ry_sq
                    if value <= 1.0:
                        inside = True
                        min_value = value
                    for off_x, off_y, blob_rx, blob_ry in blobs:
                        bx = dx - off_x
                        by = dy - off_y
                        brx_sq = float(blob_rx * blob_rx)
                        bry_sq = float(blob_ry * blob_ry)
                        value = (bx * bx) / brx_sq + (by * by) / bry_sq
                        if value <= 1.0:
                            inside = True
                            min_value = value if min_value is None else min(min_value, value)

                    if not inside and arms:
                        for cos_a, sin_a, arm_len, arm_w, offset in arms:
                            px = dx * cos_a + dy * sin_a
                            py = -dx * sin_a + dy * cos_a
                            arm_x = px - offset
                            if arm_x < -arm_len * 0.2 or arm_x > arm_len:
                                continue
                            value = (arm_x * arm_x) / (arm_len * arm_len) + (py * py) / (arm_w * arm_w)
                            if value <= 1.0:
                                inside = True
                                min_value = value if min_value is None else min(min_value, value)
                                break

                    if inside and carves:
                        for off_x, off_y, carve_rx, carve_ry in carves:
                            bx = dx - off_x
                            by = dy - off_y
                            crx_sq = float(carve_rx * carve_rx)
                            cry_sq = float(carve_ry * carve_ry)
                            value = (bx * bx) / crx_sq + (by * by) / cry_sq
                            if value <= 1.0:
                                inside = False
                                break

                    if not inside:
                        continue

                    if min_value is not None and min_value > edge_start:
                        threshold = 1.0 + (random.random() - 0.5) * edge_noise
                        if min_value > threshold:
                            continue
                        if min_value > 0.9 and random.random() < edge_hole_chance:
                            continue

                    nx, ny = center_x + dx, center_y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        self._register_water_source(
                            nx,
                            ny,
                            water_type="lake",
                            capacity=None,
                            max_capacity=None,
                            metadata=None,
                            body_id=body_id,
                        )

    def _create_water_body(self, capacity: Optional[float], max_capacity: Optional[float]) -> Optional[str]:
        if capacity is None and max_capacity is None:
            return None
        self._water_body_seq += 1
        body_id = f"water_body_{self._water_body_seq}"
        self._water_bodies[body_id] = {
            "capacity": capacity,
            "max_capacity": max_capacity if max_capacity is not None else capacity,
        }
        return body_id

    def _register_circle_points(
        self,
        center_x: int,
        center_y: int,
        radius: int,
        *,
        water_type: str,
        body_id: Optional[str],
        fill_step: int,
    ) -> None:
        fill_step = max(1, int(fill_step))
        radius = max(0, int(radius))
        if radius == 0:
            self._register_water_source(
                center_x,
                center_y,
                water_type=water_type,
                capacity=None,
                max_capacity=None,
                metadata=None,
                body_id=body_id,
            )
            return

        radius_sq = radius * radius
        for dx in range(-radius, radius + 1, fill_step):
            for dy in range(-radius, radius + 1, fill_step):
                if (dx * dx + dy * dy) > radius_sq:
                    continue
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._register_water_source(
                        nx,
                        ny,
                        water_type=water_type,
                        capacity=None,
                        max_capacity=None,
                        metadata=None,
                        body_id=body_id,
                    )

    def _register_ellipse_points(
        self,
        center_x: int,
        center_y: int,
        radius_x: int,
        radius_y: int,
        *,
        water_type: str,
        body_id: Optional[str],
        fill_step: int,
    ) -> None:
        fill_step = max(1, int(fill_step))
        radius_x = max(0, int(radius_x))
        radius_y = max(0, int(radius_y))
        if radius_x == 0 or radius_y == 0:
            self._register_water_source(
                center_x,
                center_y,
                water_type=water_type,
                capacity=None,
                max_capacity=None,
                metadata=None,
                body_id=body_id,
            )
            return

        rx_sq = radius_x * radius_x
        ry_sq = radius_y * radius_y
        for dx in range(-radius_x, radius_x + 1, fill_step):
            for dy in range(-radius_y, radius_y + 1, fill_step):
                if (dx * dx) * ry_sq + (dy * dy) * rx_sq > rx_sq * ry_sq:
                    continue
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._register_water_source(
                        nx,
                        ny,
                        water_type=water_type,
                        capacity=None,
                        max_capacity=None,
                        metadata=None,
                        body_id=body_id,
                    )


    def add_water_placements(self, placements: List[Dict[str, Any]]) -> None:
        """Add explicit water sources defined in configuration files."""
        for placement in placements or []:
            if not isinstance(placement, dict):
                continue

            water_type = placement.get("type", "stagnant")
            if not isinstance(water_type, str) or not water_type:
                water_type = "stagnant"

            if water_type == "river" and isinstance(placement.get("points"), list):
                points = placement["points"]
                if not points:
                    continue
                river_id = placement.get("river_id") or f"river_{self._water_id_seq + 1}"
                base_metadata = placement.get("metadata")
                base_metadata = dict(base_metadata) if isinstance(base_metadata, dict) else {}

                for segment, point in enumerate(points):
                    if not isinstance(point, dict):
                        continue
                    x = point.get("x")
                    y = point.get("y")
                    if x is None or y is None:
                        continue
                    metadata = dict(base_metadata)
                    metadata["river_id"] = river_id
                    metadata["segment"] = segment
                    self._register_water_source(
                        x,
                        y,
                        water_type="river",
                        capacity=None,
                        max_capacity=None,
                        metadata=metadata,
                    )
                continue

            x = placement.get("x")
            y = placement.get("y")
            if x is None or y is None:
                continue

            capacity = self._to_optional_float(placement.get("capacity"))
            max_capacity_input = placement.get("max_capacity")
            if max_capacity_input is None and capacity is not None:
                max_capacity = capacity
            else:
                max_capacity = self._to_optional_float(max_capacity_input)

            metadata = placement.get("metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}

            radius = placement.get("radius")
            radius_x = placement.get("radius_x")
            radius_y = placement.get("radius_y")
            if radius is not None:
                metadata["radius"] = radius
            if radius_x is not None:
                metadata["radius_x"] = radius_x
            if radius_y is not None:
                metadata["radius_y"] = radius_y
            if not metadata:
                metadata = None

            self._register_water_source(
                x,
                y,
                water_type=water_type,
                capacity=capacity,
                max_capacity=max_capacity,
                metadata=metadata,
            )

    # ------------------------------------------------------------------
    # Water management helpers

    def water_has_supply(self, water: Dict[str, Any]) -> bool:
        """Return True if the source still provides drinkable water."""
        body_id = water.get("body_id")
        if body_id and body_id in self._water_bodies:
            capacity = self._water_bodies[body_id].get("capacity")
            if capacity is None:
                return True
            return capacity > 0.0
        if water.get("capacity") is None:
            return True
        return water.get("capacity", 0.0) > 0.0

    def consume_water(self, water: Dict[str, Any], amount: float = 10.0) -> bool:
        """Consume water from the source, returning True if successful."""
        if water not in self.water_sources:
            return False

        body_id = water.get("body_id")
        if body_id and body_id in self._water_bodies:
            capacity = self._water_bodies[body_id].get("capacity")
            if capacity is None:
                return True
            if capacity <= 0:
                return False
            remaining = max(0.0, capacity - amount)
            self._water_bodies[body_id]["capacity"] = remaining
            return True

        capacity = water.get("capacity")
        if capacity is None:
            return True

        if capacity <= 0:
            return False

        remaining = max(0.0, capacity - amount)
        water["capacity"] = remaining
        return True

    def refill_water_source(self, source_id: str, amount: float) -> Optional[Dict[str, Any]]:
        """Refill a limited source up to its maximum capacity."""
        water = self.get_water_by_id(source_id)
        if water is None:
            if source_id in self._water_bodies:
                capacity = self._water_bodies[source_id].get("capacity")
                if capacity is None:
                    return None
                max_capacity = self._water_bodies[source_id].get("max_capacity", capacity)
                self._water_bodies[source_id]["capacity"] = min(max_capacity, capacity + amount)
            return None

        body_id = water.get("body_id")
        if body_id and body_id in self._water_bodies:
            capacity = self._water_bodies[body_id].get("capacity")
            if capacity is None:
                return water
            max_capacity = self._water_bodies[body_id].get("max_capacity", capacity)
            self._water_bodies[body_id]["capacity"] = min(max_capacity, capacity + amount)
            return water

        capacity = water.get("capacity")
        if capacity is None:
            return water

        max_capacity = water.get("max_capacity", capacity)
        water["capacity"] = min(max_capacity, capacity + amount)
        return water

    def drain_water_source(self, source_id: str, amount: float) -> Optional[Dict[str, Any]]:
        """Drain water from a limited source without removing it."""
        water = self.get_water_by_id(source_id)
        if water is None:
            if source_id in self._water_bodies:
                capacity = self._water_bodies[source_id].get("capacity")
                if capacity is None:
                    return None
                self._water_bodies[source_id]["capacity"] = max(0.0, capacity - amount)
            return None

        body_id = water.get("body_id")
        if body_id and body_id in self._water_bodies:
            capacity = self._water_bodies[body_id].get("capacity")
            if capacity is None:
                return water
            self._water_bodies[body_id]["capacity"] = max(0.0, capacity - amount)
            return water

        capacity = water.get("capacity")
        if capacity is None:
            return water

        water["capacity"] = max(0.0, capacity - amount)
        return water

    def get_water_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        for water in self.water_sources:
            if water.get("id") == source_id:
                return water
        return None
    
    # ------------------------------------------------------------------
    # Terrain generation helpers
    
    def generate_terrain(self, default_tile: int = 0) -> None:
        """Generate a simple terrain grid filled with a default tile type. In the futur we can expand this to more complex terrain generation. (Bruit de Perlin or Biome generation)"""
        self.terrain = [
            [default_tile for _ in range(self.width)]
            for _ in range(self.height)
        ]


    # ------------------------------------------------------------------
    # Lookup helpers

    def get_nearest_food(
        self,
        x: float,
        y: float,
        *,
        diet: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        candidates = [
            food
            for food in self.food_sources
            if self.food_has_supply(food) and self._food_matches_diet(food, diet)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda food: (food["x"] - x) ** 2 + (food["y"] - y) ** 2)

    def water_depth_at(self, x: float, y: float) -> Optional[float]:
        key = (int(round(x)), int(round(y)))
        return self._water_tile_depth.get(key)

    def can_entity_enter(self, entity: Any, x: float, y: float) -> bool:
        depth = self.water_depth_at(x, y)
        if depth is None:
            return True

        traits = None
        if hasattr(entity, "get_traits"):
            traits = entity.get_traits()
        if not isinstance(traits, dict):
            traits = getattr(entity, "traits", {})
        if not isinstance(traits, dict):
            traits = {}

        water_traits = traits.get("water") if isinstance(traits.get("water"), dict) else {}

        # Juvenile limits if provided.
        age_stage = getattr(entity, "age_stage", None)
        if age_stage in {"calf", "juvenile", "cub"}:
            juvenile_max = water_traits.get("juvenile_max_depth")
            if juvenile_max is not None:
                try:
                    return depth <= float(juvenile_max)
                except (TypeError, ValueError):
                    pass

        can_swim = water_traits.get("can_swim")
        max_depth = water_traits.get("max_depth")
        if max_depth is None:
            max_depth = water_traits.get("max_water_depth")

        if can_swim is True:
            if max_depth is None:
                return True
            try:
                return depth <= float(max_depth)
            except (TypeError, ValueError):
                return True

        if max_depth is not None:
            try:
                return depth <= float(max_depth)
            except (TypeError, ValueError):
                return False

        height = water_traits.get("height")
        if height is None:
            height = traits.get("height")
        if height is not None:
            try:
                return depth <= float(height) * 0.8
            except (TypeError, ValueError):
                return False

        return False


    def _is_shore_water(self, water: Dict[str, Any], *, radius: int = 1) -> bool:
        wx = int(round(float(water.get("x", 0.0))))
        wy = int(round(float(water.get("y", 0.0))))
        if not self.is_water_at(wx, wy):
            return False
        r = max(1, int(radius))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = wx + dx
                ny = wy + dy
                if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                    continue
                if not self.is_water_at(nx, ny):
                    return True
        return False

    def is_water_at(self, x: float, y: float) -> bool:
        key = (int(round(x)), int(round(y)))
        return key in self._water_tiles

    def relocate_off_water(
        self,
        x: float,
        y: float,
        *,
        attempts: int = RELOCATE_OFF_WATER_ATTEMPTS,
        radius: int = RELOCATE_OFF_WATER_RADIUS,
    ) -> Optional[Tuple[float, float]]:
        position = self._relocate_off_water(x, y, attempts=attempts, radius=radius)
        return position if position is not None else (x, y)

    def _relocate_off_water(
        self,
        x: float,
        y: float,
        *,
        attempts: int = RELOCATE_OFF_WATER_FALLBACK_ATTEMPTS,
        radius: int = RELOCATE_OFF_WATER_FALLBACK_RADIUS,
    ) -> Optional[Tuple[float, float]]:
        if not self.is_water_at(x, y):
            return (x, y)
        for _ in range(attempts):
            nx = x + random.randint(-radius, radius)
            ny = y + random.randint(-radius, radius)
            nx = self._clamp_coordinate(nx, self.width)
            ny = self._clamp_coordinate(ny, self.height)
            if not self.is_water_at(nx, ny):
                return (nx, ny)
        return None


    def find_shore_tile(
        self,
        x: float,
        y: float,
        max_radius: int,
        *,
        min_radius: int = 0,
    ) -> Optional[Tuple[float, float]]:
        """Return the nearest land tile adjacent to water within the given radius."""
        start_x = int(round(x))
        start_y = int(round(y))
        r_start = max(0, int(min_radius))
        r_end = max(r_start, int(max_radius))

        for radius in range(r_start, r_end + 1):
            best = None
            best_dist = None
            # Top/bottom edges
            for dx in range(-radius, radius + 1):
                for dy in (-radius, radius):
                    nx = start_x + dx
                    ny = start_y + dy
                    if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                        continue
                    if self.is_water_at(nx, ny):
                        continue
                    if not self._has_water_neighbor(nx, ny):
                        continue
                    if self._line_blocked_by_water(start_x, start_y, nx, ny):
                        continue
                    dist_sq = (nx - x) ** 2 + (ny - y) ** 2
                    if best is None or dist_sq < best_dist:
                        best = (float(nx), float(ny))
                        best_dist = dist_sq
            # Left/right edges (skip corners already checked)
            if radius > 0:
                for dy in range(-radius + 1, radius):
                    for dx in (-radius, radius):
                        nx = start_x + dx
                        ny = start_y + dy
                        if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                            continue
                        if self.is_water_at(nx, ny):
                            continue
                        if not self._has_water_neighbor(nx, ny):
                            continue
                        dist_sq = (nx - x) ** 2 + (ny - y) ** 2
                        if best is None or dist_sq < best_dist:
                            best = (float(nx), float(ny))
                            best_dist = dist_sq
            if best is not None:
                return best

        return None

    def _line_blocked_by_water(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        *,
        step: int = 3,
    ) -> bool:
        """Return True if a straight line crosses water tiles."""
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps <= 1:
            return False
        stride = max(1, int(step))
        for i in range(stride, steps, stride):
            t = i / steps
            nx = int(round(x0 + dx * t))
            ny = int(round(y0 + dy * t))
            if self.is_water_at(nx, ny):
                return True
        return False

    def _has_water_neighbor(self, x: int, y: int) -> bool:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x + dx
                ny = y + dy
                if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                    continue
                if self.is_water_at(nx, ny):
                    return True
        return False

    def distance_to_water(self, x: float, y: float, water: Dict[str, Any]) -> float:
        dx = x - float(water.get("x", 0.0))
        dy = y - float(water.get("y", 0.0))
        dist = math.sqrt(dx * dx + dy * dy)

        metadata = water.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        radius_x = metadata.get("radius_x") or water.get("radius_x")
        radius_y = metadata.get("radius_y") or water.get("radius_y")
        if radius_x is not None and radius_y is not None:
            rx = float(radius_x)
            ry = float(radius_y)
            if rx <= 0 or ry <= 0:
                return dist
            if dist == 0:
                return 0.0
            denom = math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
            if denom <= 1.0:
                return 0.0
            t = 1.0 / denom
            return dist * (1.0 - t)

        radius = metadata.get("radius") or water.get("radius")
        if radius is not None:
            rad = float(radius)
            return max(0.0, dist - rad)

        return dist



    def find_drink_target(
        self,
        x: float,
        y: float,
        water: Dict[str, Any],
        *,
        search_radius: int = DRINK_TARGET_SEARCH_RADIUS,
    ) -> Tuple[float, float]:
        """Return a reachable land tile close to the given water source."""
        wx = int(round(float(water.get("x", 0.0))))
        wy = int(round(float(water.get("y", 0.0))))
        if not self.is_water_at(wx, wy):
            return (float(water.get("x", 0.0)), float(water.get("y", 0.0)))

        max_radius = max(1, int(search_radius))
        best: Optional[Tuple[float, float]] = None
        best_dist = None
        for dx in range(-max_radius, max_radius + 1):
            for dy in range(-max_radius, max_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                if dx * dx + dy * dy > max_radius * max_radius:
                    continue
                nx = wx + dx
                ny = wy + dy
                if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                    continue
                if self.is_water_at(nx, ny):
                    continue
                dist_sq = (nx - x) ** 2 + (ny - y) ** 2
                if best is None or dist_sq < best_dist:
                    best = (float(nx), float(ny))
                    best_dist = dist_sq
        if best is None:
            return (float(water.get("x", 0.0)), float(water.get("y", 0.0)))
        return best

    def get_nearest_water(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        if not self.water_sources:
            return None

        max_radius = max(self.width, self.height)
        start_x = int(round(x))
        start_y = int(round(y))
        for radius in range(0, max_radius + 1):
            best = None
            best_dist = None
            # Top/bottom edges
            for dx in range(-radius, radius + 1):
                for dy in (-radius, radius):
                    nx = start_x + dx
                    ny = start_y + dy
                    if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                        continue
                    key = (nx, ny)
                    if key not in self._water_tiles:
                        continue
                    water = self._water_tile_lookup.get(key)
                    if water is None or not self.water_has_supply(water):
                        continue
                    if not self._is_shore_water(water):
                        continue
                    dist_sq = (nx - x) ** 2 + (ny - y) ** 2
                    if best is None or dist_sq < best_dist:
                        best = water
                        best_dist = dist_sq
            # Left/right edges (skip corners already checked)
            if radius > 0:
                for dy in range(-radius + 1, radius):
                    for dx in (-radius, radius):
                        nx = start_x + dx
                        ny = start_y + dy
                        if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                            continue
                        key = (nx, ny)
                        if key not in self._water_tiles:
                            continue
                        water = self._water_tile_lookup.get(key)
                        if water is None or not self.water_has_supply(water):
                            continue
                        if not self._is_shore_water(water):
                            continue
                        dist_sq = (nx - x) ** 2 + (ny - y) ** 2
                        if best is None or dist_sq < best_dist:
                            best = water
                            best_dist = dist_sq
            if best is not None:
                return best

        # Fallback: any water source if shore search failed
        drinkable = [water for water in self.water_sources if self.water_has_supply(water)]
        if not drinkable:
            return None
        return min(drinkable, key=lambda water: self.distance_to_water(x, y, water))

    def get_time_info(self, step_index: int) -> Dict[str, int | bool]:
        total_minutes = step_index * self.minutes_per_step
        hour = (total_minutes // 60) % 24
        return {
            "hour": hour,
            "is_day": DAY_START_HOUR <= hour < DAY_END_HOUR,  # jour de 6h a 20h
        }

    def consume_food(self, food: Dict[str, Any], requested_amount: float) -> Dict[str, Any]:
        """Consume a portion of a food source, returning metadata about the operation."""
        if food not in self.food_sources:
            return {"consumed": 0.0, "removed": False, "food": None}

        remaining = float(food.get("remaining_nutrition", food.get("nutrition", 0.0)))
        requested = max(0.0, float(requested_amount))
        if remaining <= 0.0 or requested <= 0.0:
            return {"consumed": 0.0, "removed": False, "food": self._snapshot_food(food)}

        consumed = min(remaining, requested)
        new_remaining = remaining - consumed
        food["remaining_nutrition"] = new_remaining
        removed = False
        if new_remaining <= 0.0:
            self.food_sources.remove(food)
            removed = True

        snapshot = self._snapshot_food(food, override_remaining=new_remaining)
        return {"consumed": consumed, "removed": removed, "food": snapshot}

    def food_has_supply(self, food: Dict[str, Any]) -> bool:
        if food not in self.food_sources:
            return False
        return food.get("remaining_nutrition", food.get("nutrition", 0.0)) > 0.0

    def food_matches_diet(self, food: Dict[str, Any], diet: Optional[str]) -> bool:
        return self._food_matches_diet(food, diet)

    # ------------------------------------------------------------------
    # Internal helpers

    def _register_water_source(
        self,
        x: float,
        y: float,
        *,
        water_type: str,
        capacity: Optional[float],
        max_capacity: Optional[float],
        metadata: Optional[Dict[str, Any]] = None,
        body_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._water_id_seq += 1
        water: Dict[str, Any] = {
            "id": f"water_{self._water_id_seq}",
            "type": water_type,
            "x": float(self._clamp_coordinate(x, self.width)),
            "y": float(self._clamp_coordinate(y, self.height)),
            "capacity": capacity,
            "max_capacity": max_capacity,
        }
        if metadata:
            water["metadata"] = metadata
        if body_id:
            water["body_id"] = body_id
        key = (int(round(water["x"])), int(round(water["y"])))
        self._water_tiles.add(key)
        self._water_tile_lookup[key] = water
        depth = self._water_depth_by_type.get(water_type, DEFAULT_WATER_DEPTH)
        previous = self._water_tile_depth.get(key)
        if previous is None or depth > previous:
            self._water_tile_depth[key] = depth
        self.water_sources.append(water)
        return water

    def _register_food_source(
        self,
        x: float,
        y: float,
        *,
        food_type: str,
        nutrition: Optional[float],
        metadata: Optional[Dict[str, Any]] = None,
        food_class: str = "plant",
    ) -> Dict[str, Any]:
        self._food_id_seq += 1
        nutrition_value = float(nutrition) if nutrition is not None else DEFAULT_FOOD_NUTRITION
        food: Dict[str, Any] = {
            "id": f"food_{self._food_id_seq}",
            "type": food_type,
            "food_class": food_class,
            "x": float(self._clamp_coordinate(x, self.width)),
            "y": float(self._clamp_coordinate(y, self.height)),
            "nutrition": nutrition_value,
            "remaining_nutrition": nutrition_value,
            "max_nutrition": nutrition_value,
        }
        metadata_payload = dict(metadata) if isinstance(metadata, dict) else None
        if metadata_payload:
            food["metadata"] = metadata_payload
        self.food_sources.append(food)
        return food

    def add_carcass(self, species: Any) -> Dict[str, Any]:
        """Create a carnivore food source at the species position."""
        nutrition_value = getattr(species, "body_nutrition", DEFAULT_CARCASS_NUTRITION)
        carcass = self._register_food_source(
            species.x,
            species.y,
            food_type="carcass",
            nutrition=nutrition_value,
            metadata={"source_species": species.name},
            food_class="meat",
        )
        return self._snapshot_food(carcass)

    @staticmethod
    def _clamp_coordinate(value: float, bound: int) -> float:
        return max(0.0, min(float(bound), float(value)))

    @staticmethod
    def _to_optional_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _food_matches_diet(food: Dict[str, Any], diet: Optional[str]) -> bool:
        if diet is None or diet == "omnivore":
            return True
        food_class = food.get("food_class", "plant")
        if diet == "herbivore":
            return food_class in {"plant", "fungi"}
        if diet == "carnivore":
            return food_class in {"meat", "carrion"}
        return True

    @staticmethod
    def _snapshot_food(food: Dict[str, Any], *, override_remaining: Optional[float] = None) -> Dict[str, Any]:
        snapshot = {
            "id": food.get("id"),
            "type": food.get("type"),
            "food_class": food.get("food_class"),
            "x": food.get("x"),
            "y": food.get("y"),
            "nutrition": food.get("nutrition"),
            "remaining_nutrition": override_remaining
            if override_remaining is not None
            else food.get("remaining_nutrition", food.get("nutrition")),
            "max_nutrition": food.get("max_nutrition", food.get("nutrition")),
        }
        metadata = food.get("metadata")
        if metadata is not None:
            snapshot["metadata"] = metadata
        return snapshot
