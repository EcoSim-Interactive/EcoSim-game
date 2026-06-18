"""Point d'entree en ligne de commande pour executer une simulation."""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

if __package__ in {
    None,
    "",
}:  # Autorise l'execution directe du fichier en mode script.
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from app.config import (
        DEFAULT_SETTINGS,  # type: ignore  # pylint: disable=import-error
    )
    from app.world_loader import (  # type: ignore  # pylint: disable=import-error
        load_world,
        load_world_and_species,
    )
    from domain import World  # type: ignore  # pylint: disable=import-error
    from simulation import (
        Simulation,  # type: ignore  # pylint: disable=import-error
    )
else:
    from domain import World
    from simulation import Simulation

    from .config import DEFAULT_SETTINGS
    from .world_loader import load_world, load_world_and_species


logger = logging.getLogger(__name__)


def build_default_world(config_path: str | None = None) -> World:
    """Construit le monde par defaut a partir du fichier
    de configuration choisi.
    """

    path = (
        config_path
        if config_path is not None
        else DEFAULT_SETTINGS.world_config_path
    )
    return load_world(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Declare les options supportees par l'interface CLI."""

    parser = argparse.ArgumentParser(
        description="Run the ecosystem simulation once."
    )
    parser.add_argument(
        "--steps", type=int, help="Override number of steps to simulate."
    )
    parser.add_argument(
        "--world-config", help="Alternative world configuration file."
    )
    parser.add_argument(
        "--write-logs",
        action="store_true",
        help="Persist JSON logs (simulation + per-entity files).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display per-step logs in the console.",
    )
    parser.add_argument(
        "--seed", type=int, help="Fix the random seed for deterministic runs."
    )
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> None:
    """Charge le monde, execute la simulation, puis journalise le resultat."""

    args = parse_args(argv)
    settings = replace(
        DEFAULT_SETTINGS,
        steps=args.steps if args.steps is not None else DEFAULT_SETTINGS.steps,
        verbose=args.verbose,
        write_logs=args.write_logs or DEFAULT_SETTINGS.write_logs,
        world_config_path=args.world_config
        or DEFAULT_SETTINGS.world_config_path,
        seed=args.seed if args.seed is not None else DEFAULT_SETTINGS.seed,
    )

    if settings.seed is not None:
        random.seed(settings.seed)

    world, species = load_world_and_species(settings.world_config_path)

    simulation = Simulation(
        world,
        species,
        steps=settings.steps,
        verbose=settings.verbose,
        write_logs=settings.write_logs,
        logs_dir=settings.logs_dir,
        seed=settings.seed,
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

    duration = simulation.last_generation_duration or (
        time.perf_counter() - start
    )

    if settings.verbose:
        logger.info("Simulation terminee : %s", simulation.to_json())
    else:
        logger.info("Simulation terminee.")
    logger.info("Temps d'execution : %.3f s", duration)
    if settings.seed is not None:
        logger.info("Seed utilise : %d", settings.seed)
    if settings.write_logs:
        logger.info("Logs disponibles dans le dossier: %s", settings.logs_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    run_cli()
