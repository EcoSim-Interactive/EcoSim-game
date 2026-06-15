"""Composant gérant l'indexation spatiale des entités du monde."""
import math
from typing import Any, Callable, Dict, List, Optional, Tuple


class SpatialIndex:
    """Index spatial 2D basé sur une grille (buckets) pour des recherches de proximité rapides."""

    def __init__(self, cell_size: int, world_width: int, world_height: int):
        self.cell_size = max(1, int(cell_size))
        self.world_width = world_width
        self.world_height = world_height
        self._index: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self._max_radius = max(1, math.ceil(max(self.world_width, self.world_height) / self.cell_size))

    def _bucket_key(self, x: float, y: float) -> Tuple[int, int]:
        return (int(float(x)) // self.cell_size, int(float(y)) // self.cell_size)

    def insert(self, entry: Dict[str, Any]) -> None:
        """Insère une entité dans l'index. L'entité doit avoir des clés 'x' et 'y'."""
        bucket = self._bucket_key(float(entry.get("x", 0.0)), float(entry.get("y", 0.0)))
        self._index.setdefault(bucket, []).append(entry)

    def remove(self, entry: Dict[str, Any]) -> None:
        """Retire une entité de l'index."""
        bucket = self._bucket_key(float(entry.get("x", 0.0)), float(entry.get("y", 0.0)))
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
        """Vide l'index."""
        self._index.clear()

    def _iter_bucket_ring(self, center_x: int, center_y: int, radius: int):
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
        """Cherche l'entité la plus proche vérifiant le prédicat."""
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
            if best_dist is not None and radius > 0 and best_dist <= (radius * self.cell_size) ** 2:
                break
        return best
