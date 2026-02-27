"""Command line entry point for the simulator."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace
from pathlib import Path

if __package__ in {None, ""}:  # Allow running as a script (python app/main.py)
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from domain import World  # type: ignore  # pylint: disable=import-error
    from simulation import Simulation  # type: ignore  # pylint: disable=import-error
    from app.config import DEFAULT_SETTINGS  # type: ignore  # pylint: disable=import-error
    from app.world_loader import (  # type: ignore  # pylint: disable=import-error
        load_world,
        load_world_and_species,
    )
else:
    from domain import World
    from simulation import Simulation
    from .config import DEFAULT_SETTINGS
    from .world_loader import load_world, load_world_and_species


logger = logging.getLogger(__name__)


def build_default_world(config_path: str | None = None) -> World:
    path = config_path if config_path is not None else DEFAULT_SETTINGS.world_config_path
    return load_world(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ecosystem simulation once.")
    parser.add_argument("--steps", type=int, help="Override number of steps to simulate.")
    parser.add_argument("--world-config", help="Alternative world configuration file.")
    parser.add_argument("--write-logs", action="store_true", help="Persist JSON logs (simulation + per-entity files).")
    parser.add_argument("--verbose", action="store_true", help="Display per-step logs in the console.")
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = replace(
        DEFAULT_SETTINGS,
        steps=args.steps if args.steps is not None else DEFAULT_SETTINGS.steps,
        verbose=args.verbose,
        write_logs=args.write_logs or DEFAULT_SETTINGS.write_logs,
        world_config_path=args.world_config or DEFAULT_SETTINGS.world_config_path,
    )

    world, species = load_world_and_species(settings.world_config_path)

    simulation = Simulation(
        world,
        species,
        steps=settings.steps,
        verbose=settings.verbose,
        write_logs=settings.write_logs,
        logs_dir=settings.logs_dir,
    )

    start = time.perf_counter()

    if settings.write_logs:
        simulation.generate_all_steps(persist=True)
        if simulation.last_generation_duration is None:
            simulation.last_generation_duration = time.perf_counter() - start
    else:
        while not simulation.is_finished():
            simulation.step_once()
        simulation.last_generation_duration = time.perf_counter() - start

    duration = simulation.last_generation_duration or (time.perf_counter() - start)

    if settings.verbose:
        logger.info("Simulation terminee : %s", simulation.to_json())
    else:
        logger.info("Simulation terminee.")
    logger.info("Temps d'execution : %.3f s", duration)
    if settings.write_logs:
        logger.info("Logs disponibles dans le dossier: %s", settings.logs_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    run_cli()
