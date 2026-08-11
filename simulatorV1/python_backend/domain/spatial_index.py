"""2D grid-based spatial index for fast proximity queries."""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple


class SpatialIndex:
    """2D grid spatial index (bucketed grid) for fast O(1) proximity queries.

    Attributes:
        cell_size (int): Grid cell dimension in coordinate units.
        world_width (int): Total map width.
        world_height (int): Total map height.
    """

    def __init__(self, cell_size: int, world_width: int, world_height: int):
        """Initializes SpatialIndex with dimensions and bucket configuration.

        Args:
            cell_size (int): Target width/height of individual spatial buckets.
            world_width (int): Total width of the simulation grid.
            world_height (int): Total height of the simulation grid.
        """
        self.cell_size = max(1, int(cell_size))
        self.world_width = world_width
        self.world_height = world_height
        self._index: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self._max_radius = max(
            1,
            math.ceil(
                max(self.world_width, self.world_height) / self.cell_size
            ),
        )

    def _bucket_key(self, x: float, y: float) -> Tuple[int, int]:
        """Computes grid bucket key for spatial coordinates."""
        return (
            int(float(x)) // self.cell_size,
            int(float(y)) // self.cell_size,
        )

    def insert(self, entry: Dict[str, Any]) -> None:
        """Inserts an entity dictionary into the spatial index.

        Args:
            entry (Dict[str, Any]): Entity containing 'x' and 'y' keys.
        """
        bucket = self._bucket_key(
            float(entry.get("x", 0.0)), float(entry.get("y", 0.0))
        )
        self._index.setdefault(bucket, []).append(entry)

    def remove(self, entry: Dict[str, Any]) -> None:
        """Removes an entity dictionary from the spatial index.

        Args:
            entry (Dict[str, Any]): Entity to remove.
        """
        bucket = self._bucket_key(
            float(entry.get("x", 0.0)), float(entry.get("y", 0.0))
        )
        bucket_entries = self._index.get(bucket)
        if not bucket_entries:
            return
        try:
            bucket_entries.remove(entry)
        except ValueError:
            return
        if not bucket_entries:
            self._index.pop(bucket, None)

    def clear(self) -> None:
        """Clears all spatial index entries."""
        self._index.clear()

    def _iter_bucket_ring(self, center_x: int, center_y: int, radius: int):
        """Yields bucket keys along a concentric ring at a given radius."""
        if radius <= 0:
            yield (center_x, center_y)
            return
        for dx in range(-radius, radius + 1):
            yield (center_x + dx, center_y - radius)
            yield (center_x + dx, center_y + radius)
        for dy in range(-radius + 1, radius):
            yield (center_x - radius, center_y + dy)
            yield (center_x + radius, center_y + dy)

    def search_nearest(
        self,
        x: float,
        y: float,
        *,
        predicate: Callable[[Dict[str, Any]], bool],
        distance_fn: Callable[[Dict[str, Any]], float],
    ) -> Optional[Dict[str, Any]]:
        """Searches for nearest entity matching predicate within spatial rings.

        Args:
            x (float): Target search x position.
            y (float): Target search y position.
            predicate (Callable): Filter matching candidate entities.
            distance_fn (Callable): Function computing squared distance.

        Returns:
            Optional[Dict[str, Any]]: Nearest matching entity dictionary.
        """
        if not self._index:
            return None

        start_x, start_y = self._bucket_key(x, y)
        best: Optional[Dict[str, Any]] = None
        best_dist: Optional[float] = None

        for radius in range(0, self._max_radius + 1):
            for bucket in self._iter_bucket_ring(start_x, start_y, radius):
                for entry in self._index.get(bucket, ()):
                    if not predicate(entry):
                        continue
                    dist_sq = float(distance_fn(entry))
                    if best_dist is None or dist_sq < best_dist:
                        best = entry
                        best_dist = dist_sq
            if (
                best_dist is not None
                and radius > 0
                and best_dist <= (radius * self.cell_size) ** 2
            ):
                break
        return best
