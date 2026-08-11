"""Social and advanced behavior modules for animal simulation engine."""

from .grouping import maintain_group_cohesion
from .predation import execute_predation_cycle
from .scavenging import seek_carcass_opportunity
from .territory import enforce_territory

__all__ = [
    "maintain_group_cohesion",
    "enforce_territory",
    "execute_predation_cycle",
    "seek_carcass_opportunity",
]
