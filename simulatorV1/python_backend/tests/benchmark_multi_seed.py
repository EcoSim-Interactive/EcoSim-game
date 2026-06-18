"""Lance une campagne de benchmarks multi-seeds sur un meme scenario."""

from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORLD_CONFIG = BACKEND_ROOT / "app" / "world_config.json"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.world_loader import load_world_and_species  # noqa: E402
from simulation import SimulationEngine  # noqa: E402
from simulation.animal import Animal  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Declare les options de la campagne de benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark la simulation sur plusieurs seeds."
    )
    parser.add_argument(
        "--steps", type=int, default=1000, help="Nombre de steps par run."
    )
    parser.add_argument(
        "--seeds",
        default="1,2,3,4,5",
        help="Liste de seeds separees par des virgules. Exemple: 10,11,12",
    )
    parser.add_argument(
        "--world-config",
        default=str(DEFAULT_WORLD_CONFIG),
        help="Chemin du fichier de configuration monde.",
    )
    parser.add_argument(
        "--write-logs",
        action="store_true",
        help="Ecrit les logs complets pendant le benchmark.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Active les logs console de chaque run.",
    )
    parser.add_argument(
        "--output-json",
        help="Chemin optionnel pour sauvegarder le rapport JSON.",
    )
    return parser.parse_args(argv)


def parse_seed_list(raw_value: str) -> List[int]:
    """Convertit une chaine CSV en liste de seeds uniques conservees dans l'ordre."""  # noqa: E501
    seeds: List[int] = []
    seen: set[int] = set()
    for chunk in (raw_value or "").split(","):
        value = chunk.strip()
        if not value:
            continue
        seed = int(value)
        if seed in seen:
            continue
        seen.add(seed)
        seeds.append(seed)
    if not seeds:
        raise ValueError("Au moins une seed doit etre fournie.")
    return seeds


def summarize_species(summary: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Construit un resume vivant/mort par espece a partir du summary final."""
    result: Dict[str, Dict[str, int]] = {}
    for item in summary.get("species", []):
        species_type = str(item.get("species_type", "unknown"))
        vitality = float(item.get("vitality", 0.0))
        bucket = result.setdefault(
            species_type, {"alive": 0, "dead": 0, "total": 0}
        )
        bucket["total"] += 1
        if vitality > 0.0:
            bucket["alive"] += 1
        else:
            bucket["dead"] += 1
    return result


def run_single_benchmark(
    *,
    seed: int,
    steps: int,
    world_config: str | None,
    write_logs: bool,
    verbose: bool,
) -> Dict[str, Any]:
    """Execute un run unique et renvoie les mesures utiles au benchmark."""
    random.seed(seed)
    Animal.reset_shared_states()
    Animal._id_sequence = itertools.count(1)

    world, species = load_world_and_species(world_config)
    simulation = SimulationEngine(
        world,
        species,
        steps=steps,
        verbose=verbose,
        write_logs=write_logs,
        seed=seed,
    )

    wall_start = time.perf_counter()
    if write_logs:
        simulation.generate_all_steps(persist=True)
    else:
        simulation.run()
    wall_duration = time.perf_counter() - wall_start

    summary = simulation.save_summary()
    total = len(summary.get("species", []))
    alive = sum(
        1
        for item in summary.get("species", [])
        if float(item.get("vitality", 0.0)) > 0.0
    )

    return {
        "seed": seed,
        "steps": steps,
        "engine_seconds": float(simulation.last_generation_duration or 0.0),
        "wall_seconds": wall_duration,
        "alive": alive,
        "dead": total - alive,
        "total": total,
        "remaining_food": int(summary.get("remaining_food", 0)),
        "remaining_water": int(summary.get("remaining_water", 0)),
        "species": summarize_species(summary),
        "summary_file": simulation.summary_file,
        "simulation_file": simulation.steps_file,
    }


def build_aggregate_report(runs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrege les indicateurs principaux pour comparer les seeds entre elles."""  # noqa: E501
    run_list = list(runs)
    engine_values = [float(item["engine_seconds"]) for item in run_list]
    wall_values = [float(item["wall_seconds"]) for item in run_list]
    alive_values = [int(item["alive"]) for item in run_list]
    dead_values = [int(item["dead"]) for item in run_list]

    def _stats(values: List[float]) -> Dict[str, float]:
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
        }

    return {
        "run_count": len(run_list),
        "engine_seconds": _stats(engine_values),
        "wall_seconds": _stats(wall_values),
        "alive": _stats([float(value) for value in alive_values]),
        "dead": _stats([float(value) for value in dead_values]),
    }


def print_report(report: Dict[str, Any]) -> None:
    """Affiche un rapport console lisible rapidement."""
    print("=== Benchmark Multi-Seed ===")
    print(f"runs={report['aggregate']['run_count']}")
    engine = report["aggregate"]["engine_seconds"]
    wall = report["aggregate"]["wall_seconds"]
    print(
        "engine_seconds "
        f"mean={engine['mean']:.3f} median={engine['median']:.3f} "
        f"min={engine['min']:.3f} max={engine['max']:.3f}"
    )
    print(
        "wall_seconds "
        f"mean={wall['mean']:.3f} median={wall['median']:.3f} "
        f"min={wall['min']:.3f} max={wall['max']:.3f}"
    )
    print()
    for run in report["runs"]:
        print(
            f"seed={run['seed']} steps={run['steps']} "
            f"engine={run['engine_seconds']:.3f}s wall={run['wall_seconds']:.3f}s "  # noqa: E501
            f"alive={run['alive']}/{run['total']} dead={run['dead']} "
            f"food={run['remaining_food']} water={run['remaining_water']}"
        )
        for species_type, values in sorted(run["species"].items()):
            print(
                f"  species={species_type} "
                f"alive={values['alive']}/{values['total']} dead={values['dead']}"  # noqa: E501
            )


def main(argv: list[str] | None = None) -> int:
    """Point d'entree CLI du benchmark multi-seeds."""
    args = parse_args(argv)
    seeds = parse_seed_list(args.seeds)

    runs = [
        run_single_benchmark(
            seed=seed,
            steps=args.steps,
            world_config=args.world_config,
            write_logs=args.write_logs,
            verbose=args.verbose,
        )
        for seed in seeds
    ]
    report = {
        "config": {
            "steps": args.steps,
            "world_config": args.world_config,
            "write_logs": args.write_logs,
            "verbose": args.verbose,
            "seeds": seeds,
        },
        "aggregate": build_aggregate_report(runs),
        "runs": runs,
    }

    print_report(report)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nrapport_json={output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
