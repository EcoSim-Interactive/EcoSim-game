# API Reference — `python_backend`

This document lists, module by module, the public classes and functions of
the Python backend, summarized from their docstrings. For the
architectural overview (WebSocket flow, run lifecycle), see
[../../ARCHITECTURE.md](../../ARCHITECTURE.md) and
[../../docs/TECHNIQUE.md](../../docs/TECHNIQUE.md). For installation and
commands (`uv run`, tests, lint), see [README.md](README.md).

Every docstring cited here can be checked directly in the source code
(`git grep '"""'`); this file is only a navigation summary, not meant to
stay an exhaustive copy as the code evolves — when in doubt, the
docstring in the code is authoritative.

## Contents

- [`app/`](#app) — configuration, CLI, species catalog, world loading
- [`domain/`](#domain) — business entities (World, Species, Animal, resources)
- [`simulation/`](#simulation) — simulation engine, AI, behaviors
- [`infrastructure/`](#infrastructure) — WebSocket server, JSON persistence
- [`scripts/`](#scripts) — utilities
- [Entry points](#entry-points)

## `app/`

Configuration and application entry points (CLI, world loading, species
catalog).

### `app/config.py`
- **`SimulationSettings`** — dataclass encapsulating the global simulation
  execution parameters (step count, tick, host/port, log paths,
  `verbose`).

### `app/main.py`
- `build_default_world()` — builds the default world from the
  configuration file.
- `parse_args()` — declares the options supported by the CLI.
- `run_cli()` — loads the world, runs the simulation, then logs the
  result.

### `app/species_catalog/store.py`
- **`SpeciesCatalogStore`** — encapsulates loading, validation, and
  persistence of the species catalog and user selections:
  - `load_catalog()` — loads and normalizes the catalog from disk.
  - `build_selection_from_catalog()` — builds a population selection from
    the catalog's defaults.
  - `sanitize_selection()` — validates and completes a raw selection
    against the catalog.
  - `load_selection()` — loads the saved selection, migrating a legacy
    file if needed.
  - `save_selection()` — persists the given selection to the dedicated
    JSON file.
  - `selection_to_species_config()` — converts a selection into a
    ready-to-simulate species config.

### `app/species_store.py`
Legacy compatibility module re-exporting the historical API
(`load_species_catalog`, `build_selection_from_catalog`,
`load_species_selection`, `save_species_selection`,
`sanitize_selection`, `selection_to_species_config`) by delegating to
`SpeciesCatalogStore`.

### `app/world_loader.py`
Loads the world and the species population from JSON files:
- `load_world()` — loads a `World` instance from a JSON config file, or
  falls back to default values.
- `load_world_and_species()` — loads both the `World` and the `Animal`
  population simultaneously.
- `load_world_from_file()` — loads a `World` strictly from a JSON file (no
  fallback).
- `load_config()` — reads a JSON config file and returns a dict with the
  base directory.
- `build_world_from_config()` — builds a `World` from a configuration
  mapping.
- `build_species_from_config()` — builds the species list from presets and
  population specs.
- `apply_food_config()` / `apply_water_config()` — applies food / water
  configuration to a `World` instance.

## `domain/`

Pure business entities, with no dependency on infrastructure.

### `domain/species.py`
- **`Species`** (abstract class) — a living entity: vital gauges (hunger,
  thirst, fatigue, vitality), movement, perception, feeding. Main
  methods:
  - `hunger` (property) — hunger gauge derived from the calorie deficit.
  - `calorie_deficit()` / `apply_calories()` / `burn_calories()` —
    calorie reserve management.
  - `distance_to()` / `move_towards()` / `random_move()` — movement.
  - `try_eat()` / `try_drink()` — consuming nearby resources.
  - `smell_for_food()` / `smell_for_water()` — olfactory perception beyond
    the field of vision.
  - `update_vitals()` — advances hunger, thirst, fatigue, and vitality by
    one step.

### `domain/world.py`
- **`World`** — central container for the grid, resources, and spatial
  rules:
  - `add_food` / `add_food_placements` — procedural generation and
    explicit placement of food.
  - `add_water` / `add_river` / `add_stagnant_pools` / `add_oasis` /
    `add_lakes` / `regenerate_water` / `add_water_placements` —
    generation, placement, and regeneration of water sources.
  - `water_has_supply()` / `consume_water()` / `refill_water_source()` /
    `drain_water_source()` / `get_water_by_id()` — lifecycle of a water
    source.
  - `generate_terrain()` — generates the terrain grid.
  - `get_nearest_food()` / `get_nearest_water()` / `distance_to_water()` /
    `find_shore_tile()` / `find_drink_target()` — proximity queries.
  - `can_entity_enter()` / `is_water_at()` / `relocate_off_water()` /
    `water_depth_at()` — tile walkability rules.
  - `get_time_info()` — derives the hour of day and day/night status for
    the step.
  - `consume_food()` / `food_has_supply()` / `food_matches_diet()` /
    `add_carcass()` — lifecycle of a food source, including carcasses
    resulting from predation.

### `domain/animal_components.py`
- **`AgeComponent`** — manages age progression and old-age mortality risk
  (`tick_age()`).
- **`MetabolismComponent`** — manages nutrition, calorie reserves, body
  mass, and carcass nutritional value (`apply_profile()`,
  `refresh_body_profile()`).

### `domain/spatial_index.py`
- **`SpatialIndex`** — 2D bucketed grid for fast proximity queries
  (amortized O(1)): `insert()`, `remove()`, `clear()`,
  `search_nearest()`.

### `domain/food_generation.py`
- `generate_food_sources()` — generates a list of food sources with plant
  profiles.
- `resolve_food_profile()` — resolves a food type identifier to a valid
  profile.

### `domain/water_generation.py`
- `generate_river_segments()` — generates the waypoints of a continuous
  river.
- `trace_line()` — traces a line of discrete coordinates (Bresenham's
  algorithm).
- `generate_stagnant_pool_specs()` / `generate_oasis_specs()` /
  `generate_lake_specs()` — generate the specs for the different types of
  water bodies.

### `domain/constants.py`
Business constants shared by the domain and simulation layers (hunger /
thirst / fatigue rates, interaction distances, vitality thresholds,
etc.).

## `simulation/`

Simulation engine and behavior logic.

### `simulation/engine.py`
- **`SimulationEngine`** — high-level orchestrator of the ecosystem
  timeline:
  - `step_once()` — runs one step for all active entities.
  - `run()` — runs the simulation to completion and returns all step
    frames.
  - `generate_all_steps()` — computes every step once, caches them, and
    optionally persists them.
  - `save_summary()` — saves the aggregate summary to disk if
    `write_logs` is enabled.
  - `is_finished()` — indicates whether the maximum step count has been
    reached.

### `simulation/animal.py`
- **`Animal`** — specialization of `Species` carrying behavioral and
  social state (identifiers, group, pack, social and water memory):
  `from_species()`, `get_traits()` / `set_trait()`, `get_group_id()` /
  `set_group_id()`, `get_pack_id()` / `set_pack_id()`,
  `remember_water()` / `recall_water()`, `remember_water_target()` /
  `recall_water_target()`, `pack_state_for()` / `group_state_for()`,
  `refresh_body_profile()`, `set_sex()` / `set_age_stage()` /
  `advance_age()`, `update_vitals()`. The `decide_idle_action`,
  `handle_thirst`, `handle_fatigue`, `handle_cycle_rest`, `handle_hunger`
  and `handle_idle` methods delegate to `simulation/ai/behavior.py`.

### `simulation/action_executor.py`
- `resolve_consumption()` — checks whether the current action results in
  the entity eating.

### `simulation/step_context.py`
- `compute_world_time()` — computes the logical time metadata for the
  active step.
- `build_step_frame()` — initializes the standard data structure for a
  step frame.
- `initialize_species_status()` / `finalize_species_status()` — captures
  an entity's initial state / injects its final state around the
  application of AI rules.
- `build_summary_payload()` — builds the final aggregate snapshot of the
  simulation.

### `simulation/event_log.py`
- **`EventLogger`** — logging facade isolating the engine from output
  handlers: `log()`, `log_step_summary()`.

### `simulation/ai/` — decision tree and elementary behaviors
- `simulation/ai/decision.py`: `process_species()` — evaluates the
  decision tree and updates an animal's serialized status on each tick.
- `simulation/ai/behavior.py`: `decide_idle_action()`,
  `handle_thirst()`, `handle_fatigue()`, `handle_cycle_rest()`,
  `handle_hunger()`, `handle_idle()` — elementary behaviors (seeking
  water/food, resting, day/night cycle handling).
- `simulation/ai/relationships.py`: `handle_species_relationships()` —
  applies social and pack behaviors before the generic survival routines.
  (`simulation/relationships.py` at the package root is a compatibility
  wrapper delegating to this module.)

### `simulation/actions/` — advanced social and territorial behaviors
- `grouping.py`: `maintain_group_cohesion()` — keeps a group compact
  without abrupt overlapping between individuals.
- `predation.py`: `execute_predation_cycle()` — drives the full
  cooperative hunting sequence, carcass sharing, and the pack's feeding
  order.
- `scavenging.py`: `seek_carcass_opportunity()` — directs a scavenger to
  an available carcass while respecting remembered priorities and past
  failures.
- `territory.py`: `enforce_territory()` — forces the animal to stay in, or
  return to, its territory when needed.

## `infrastructure/`

Network adapters and persistence.

### `infrastructure/http/server.py`
WebSocket server exposing the simulation engine to the Godot client:
- `get_world()` — initializes the world and sends its data to the client.
- `ensure_precomputed()` — guarantees the steps are precomputed before
  streaming.
- `simulation_runner()` — async task that sends one precomputed step at a
  time.
- `handle_command()` — handles each message received from the client
  (`get_world`, `compute`, `start`, `pause`, `resume`, `stop`, ...).
- `handler()` — handles the full lifecycle of a client connection.
- `format_step_summary()` — formats a step's species states into a
  one-line log summary.
- `main()` — binds the WebSocket server and serves until interrupted.

### `infrastructure/persistence/log_writer.py`
JSON persistence helpers for simulation output:
- `ensure_logs_dir()` — creates the logs directory if it doesn't exist
  yet.
- `next_run_index()` — computes the next free run index.
- `write_step()` / `write_steps_bundle()` — writes a single step / all
  computed steps to a JSON file.
- `write_summary()` — writes the simulation summary to its run directory.
- `write_entity_logs()` — splits step data into log files filtered by
  animal / group / species / diet.

## `scripts/`

### `scripts/clear_logs.py`
- `delete_logs_dirs()` — recursively removes every `logs` directory under
  the given path.

## Entry points

- `server.py` (package root) — compatibility wrapper that launches the
  WebSocket server (`infrastructure/http/server.py::main`). Usage:
  `uv run server.py`.
- `main.py` (package root) — compatibility wrapper that delegates to the
  CLI (`app/main.py::run_cli`). Usage: `uv run app/main.py`.
- `app/__init__.py::run_cli()` — loads `app.main` on demand to avoid the
  `runpy` warning when running via `python -m`.
