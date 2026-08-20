# Python Backend Server

## Project Description
This Python backend powers the ecological simulation driven by the Godot client. It exposes a bidirectional WebSocket server that receives commands, computes state changes, and then sends back real-time updates.

## Requirements
- Python >= 3.12
- [UV (Astral)](https://docs.astral.sh/uv/getting-started/installation/) for dependency management and execution.

## Installation
1. Install UV (see the official documentation above).
2. Lock the dependencies:
   ```bash
   uv lock
   ```
3. Sync the environment:
   ```bash
   uv sync
   ```

## Running the components
- WebSocket server:
  ```bash
  uv run server.py
  ```
  (the `server.py` file redirects to `infrastructure/http/server.py`).
- Offline CLI simulation:
  ```bash
  uv run app/main.py
  ```

## Tests and Code Quality
Here are the useful commands for maintaining the project's quality and reliability:

- **Run the unit tests**:
  ```bash
  uv run python -m unittest discover tests
  ```
- **Check the code with the linter (Ruff)**:
  ```bash
  uv run ruff check .
  ```
- **Automatically fix small issues detected by the linter**:
  ```bash
  uv run ruff check --fix .
  ```
- **Automatically format the code (PEP 8, line breaks, etc.)**:
  ```bash
  uv run ruff format .
  ```

## `python_backend` package architecture
```
python_backend/
|- app/                      # CLI entry point and configuration
|- domain/                   # Business model (World, Species)
|- infrastructure/
|  |- http/                 # WebSocket server
|  |- persistence/          # Writing JSON logs
|- scripts/                  # Utilities (e.g. removing logs)
|- simulation/               # Modularized simulation engine
|- tests/                    # Location for automated tests
```

The main modules:
- `simulation/engine.py` orchestrates the loop and relies on `simulation/animal.py`, `simulation/ai/` (decision.py, behavior.py, relationships.py), `simulation/actions/*` (grouping, predation, scavenging, territory), `simulation/action_executor.py` and `simulation/step_context.py`.
- `domain/` holds the pure entities (no dependency on infrastructure): `world.py`, `species.py`, `animal_components.py`, `spatial_index.py`, `food_generation.py`, `water_generation.py`.
- `app/species_catalog/store.py` centralizes loading/validation/persistence of the species catalog and user selections.
- `infrastructure/persistence/log_writer.py` centralizes writing the JSON files when the `write_logs` option is enabled.

Detailed reference for each module (classes, public functions, summary drawn from the docstrings): [REFERENCE.md](REFERENCE.md).

Each logged run generates a logX/ folder containing the main files (`simulation.json`, `summary.json`) as well as four subfolders (`animals/`, `groups/`, `species/`, `diets/`) providing histories filtered by individual, group, species, or diet.

## Dependencies
- **websockets >= 15.0.1** for real-time communication.

Add a package:
```bash
uv add <package_name>
```

## Godot Interface
Run the Godot project located in the `godot_interface` folder to consume this backend.
