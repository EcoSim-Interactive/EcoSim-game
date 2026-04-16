"""Moteur principal qui orchestre les tours de simulation et la journalisation."""
from __future__ import annotations

import copy
import json
import time
from typing import Any, Dict, List, Optional

from infrastructure.persistence import log_writer
from domain.constants import (
    EXPLORE_HUNGER_THRESHOLD,
    EXPLORE_THIRST_THRESHOLD,
    FATIGUE_CRITICAL_THRESHOLD,
    FATIGUE_MODERATE_THRESHOLD,
    HUNGER_MODERATE_THRESHOLD,
    HUNGER_OVERRIDES_THIRST_THRESHOLD,
    THIRST_BLOCKS_REST_THRESHOLD,
    THIRST_CRITICAL_THRESHOLD,
    THIRST_FORCED_EXPLORATION_THRESHOLD,
    THIRST_MODERATE_THRESHOLD,
)

from .action_executor import resolve_consumption
from .ai import decision as ai_decision
from .animal import Animal
from .event_log import EventLogger
from .step_context import (
    build_step_frame,
    build_summary_payload,
    compute_world_time,
    finalize_species_status,
    initialize_species_status,
)


class SimulationEngine:
    """Orchestrateur haut niveau de l'ecosysteme simule."""

    def __init__(
        self,
        world: Any,
        species_list: List[Any],
        steps: int = 100,
        *,
        verbose: bool = True,
        write_logs: bool = False,
        logs_dir: str = "logs",
        seed: Optional[int] = None,
    ) -> None:
        self.world = world
        Animal.reset_shared_states()
        converted_species: List[Animal] = []
        for candidate in species_list:
            animal = Animal.from_species(candidate)
            animal.set_group_id(getattr(animal, "group_id", None))
            animal.set_pack_id(getattr(animal, "pack_id", None))
            converted_species.append(animal)
        self.species_list = converted_species
        self._active_species: List[Animal] = [animal for animal in self.species_list if getattr(animal, "alive", True)]
        self.steps = steps
        self.write_logs = write_logs
        self.logs_dir = logs_dir
        self.seed = seed
        self.current_step = 0
        self.logger = EventLogger(verbose=verbose)
        self._precomputed_steps: Optional[List[Dict[str, Any]]] = None
        self._summary_cache: Optional[Dict[str, Any]] = None
        self._run_index: Optional[int] = None
        self.steps_file: Optional[str] = None
        self.summary_file: Optional[str] = None
        self.last_generation_duration: Optional[float] = None
        self._initial_world_snapshot: Dict[str, Any] = self._snapshot_world(world)
        if self.write_logs:
            log_writer.ensure_logs_dir(self.logs_dir)

    def log(self, message: str) -> None:
        self.logger.log(message)

    def is_finished(self) -> bool:
        return self.current_step >= self.steps

    # ------------------------------------------------------------------
    # Execution pas a pas de la simulation

    def step_once(self) -> Optional[Dict[str, Any]]:
        if self.is_finished():
            return None

        step_index = self.current_step
        world_time = compute_world_time(self.world, step_index)
        step_data = build_step_frame(step_index, world_time)

        for animal in list(self._active_species):
            if not getattr(animal, "alive", True):
                status = initialize_species_status(animal)
                predator_id = animal.recall_social("killed_by") if hasattr(animal, "recall_social") else None
                if predator_id is not None:
                    self.logger.log(f"{animal.name} a ete tue avant son tour par le predateur {predator_id}.")
                    status["action"] = "killed_by_predation"
                    status["motivation"] = f"attaque du predateur {predator_id}"
                else:
                    self._handle_exhaustion(animal, status)
                finalize_species_status(animal, status)
                step_data["species"].append(status)
                try:
                    self._active_species.remove(animal)
                except ValueError:
                    pass
                continue
            status = initialize_species_status(animal)
            was_alive = animal.vitality > 0
            if not was_alive:
                self._handle_exhaustion(animal, status)
            else:
                food_result = self._process_species(animal, status, world_time)

            if was_alive:
                animal.update_vitals(world_time)
                if hasattr(self.world, "minutes_per_step"):
                    animal.advance_age(getattr(self.world, "minutes_per_step", 0))
            finalize_species_status(animal, status)
            step_data["species"].append(status)
            food_result = status.get("food_event") if was_alive else None
            self._apply_food_result(food_result, step_data)

            if was_alive and animal.vitality <= 0:
                carcass = self.world.add_carcass(animal)
                step_data["new_food_sources"].append(carcass)
                try:
                    self._active_species.remove(animal)
                except ValueError:
                    pass

        self.logger.log_step_summary(step_data)
        self.current_step += 1
        return step_data

    def run(self) -> List[Dict[str, Any]]:
        if self._precomputed_steps is not None and self.is_finished():
            return list(self._precomputed_steps)

        steps_data: List[Dict[str, Any]] = []
        measured = False
        start_time = time.perf_counter()
        while not self.is_finished():
            step_data = self.step_once()
            if step_data is not None:
                steps_data.append(step_data)
                measured = True

        if measured:
            self.last_generation_duration = time.perf_counter() - start_time
        elif self.last_generation_duration is None:
            self.last_generation_duration = 0.0

        if self._precomputed_steps is None:
            self._precomputed_steps = list(steps_data)

        return steps_data

    def generate_all_steps(self, *, persist: bool = True) -> List[Dict[str, Any]]:
        """Compute every step once, cache them, and optionally persist to disk."""
        if self._precomputed_steps is None or len(self._precomputed_steps) != self.steps:
            steps_data = self.run()
        else:
            steps_data = list(self._precomputed_steps)

        if self._summary_cache is None:
            self._summary_cache = self._build_summary()

        if self.write_logs and persist:
            run_index = self._run_index or log_writer.next_run_index(self.logs_dir)
            self._run_index = run_index
            self.steps_file = log_writer.write_steps_bundle(
                self.logs_dir,
                steps_data,
                summary_data=self._summary_cache,
                world_data=self._build_world_snapshot(),
                duration_sec=self.last_generation_duration,
                index=run_index,
                compact=True,
            )
            self.summary_file = log_writer.write_summary(
                self.logs_dir,
                self._summary_cache,
                index=run_index,
            )
            log_writer.write_entity_logs(
                self.logs_dir,
                steps_data,
                index=run_index,
                summary_data=self._summary_cache,
            )

        return steps_data

    # ------------------------------------------------------------------
    # Production des sorties et des resumes

    def save_summary(self) -> Dict[str, Any]:
        if self._summary_cache is None:
            self._summary_cache = self._build_summary()
        if self.write_logs:
            run_index = self._run_index or log_writer.next_run_index(self.logs_dir)
            self._run_index = run_index
            self.summary_file = log_writer.write_summary(
                self.logs_dir,
                self._summary_cache,
                index=run_index,
            )
            if self._precomputed_steps:
                log_writer.write_entity_logs(
                    self.logs_dir,
                    self._precomputed_steps,
                    index=run_index,
                    summary_data=self._summary_cache,
                )
        return self._summary_cache

    def to_json(self) -> str:
        if self._summary_cache is None:
            self._summary_cache = self._build_summary()
        return json.dumps(self._summary_cache, indent=2)

    # ------------------------------------------------------------------
    # Helpers internes utilises pendant un run

    def _handle_exhaustion(self, animal: Animal, status: Dict[str, Any]) -> None:
        self.logger.log(f"{animal.name} est epuise.")
        status["action"] = "exhausted"
        status["motivation"] = "vitalite nulle"

    def _process_species(self, animal: Animal, status: Dict[str, Any], world_time: Dict[str, Any]) -> None:
        return ai_decision.process_species(
            animal,
            status,
            world_time,
            self.world,
            self.species_list,
            self.logger,
        )

    def _apply_food_result(self, food_event: Optional[Dict[str, Any]], step_data: Dict[str, Any]) -> None:
        if not food_event:
            return
        snapshot = dict(food_event)
        food_id = str(snapshot.get("food_id") or snapshot.get("id") or "")
        if snapshot.get("removed"):
            if food_id:
                step_data["removed_food_ids"].append(food_id)
            return
        if food_id:
            snapshot["id"] = food_id
        step_data["updated_food_sources"].append(snapshot)

    def _build_world_snapshot(self) -> Dict[str, Any]:
        """Retourne l'etat initial du monde pour les fichiers de simulation."""
        snapshot = copy.deepcopy(self._initial_world_snapshot)
        snapshot["seed"] = self.seed
        return snapshot

    def _build_summary(self) -> Dict[str, Any]:
        summary = build_summary_payload(self.species_list, self.world)
        summary["seed"] = self.seed
        return summary

    def _snapshot_world(self, world: Any) -> Dict[str, Any]:
        """Capture le monde avant le run (evite les carcasses/post-mutations)."""
        terrain = getattr(world, "terrain", None)
        if terrain in (None, []):
            if hasattr(world, "generate_terrain"):
                try:
                    world.generate_terrain()
                    terrain = getattr(world, "terrain", [])
                except Exception:
                    terrain = []
            else:
                terrain = []

        return {
            "width": getattr(world, "width", None),
            "height": getattr(world, "height", None),
            "minutes_per_step": getattr(world, "minutes_per_step", None),
            "food_sources": copy.deepcopy(getattr(world, "food_sources", [])),
            "water_sources": copy.deepcopy(getattr(world, "water_sources", [])),
            "terrain": copy.deepcopy(terrain) if terrain is not None else [],
        }
