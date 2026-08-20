# Technical Documentation

## Objective
This repository contains a pre-calculated ecosystem simulator (Python backend) and a Godot interface for real-time visualization and control.

## Essential directory structure
- `simulatorV1/python_backend`: simulation engine, WebSocket API and utilities.
- `simulatorV1/godot_interface/simulation`: Godot project (scenes + WebSocket client scripts).
- `simulatorV1/python_backend/logs`: JSON outputs (`simulationN.json`, `summaryN.json`).

## General architecture

- Python backend
  - `app/`: CLI entry points, configuration (`SimulationSettings`), world loading (`world_loader.py`) and species catalog (`species_catalog/`).
  - `domain/`: domain models (`World`, `Species`), procedural resource generation (`food_generation.py`, `water_generation.py`), spatial index (`spatial_index.py`).
  - `simulation/`: engine (`engine.py`), AI (`ai/decision.py`, `ai/behavior.py`, `ai/relationships.py`), social/territorial behaviors (`actions/`), action execution and step context.
  - `infrastructure/http`: WebSocket server (client command handling, step streaming).
  - `infrastructure/persistence`: log writing and run file management.

  Detailed module-by-module reference (derived from the code's docstrings):
  [simulatorV1/python_backend/REFERENCE.md](../simulatorV1/python_backend/REFERENCE.md).

- Godot frontend
  - `socket_client.gd` sends `get_world`, `compute`, `start`, `pause`, `resume`, `stop` and receives the `step`, `status`, `summary` payloads.

  Detailed frontend reference (scenes, scripts, client/server flow):
  [simulatorV1/godot_interface/README.md](../simulatorV1/godot_interface/README.md).

## Runtime flow (summary)
1. Client sends `get_world` -> backend returns geometry + resources.
2. Client requests `compute` -> backend runs `SimulationEngine.generate_all_steps()` (background pre-calculation) and produces the log files.
3. Client sends `start` -> backend streams one step every `tick_ms`, honoring `pause`/`stop`.
4. At the end, the backend emits a `summary` frame.

## WebSocket API (key commands)
- `get_world`: builds and returns the initial world.
- `compute`: starts pre-calculating the steps (background task).
- `start` / `pause` / `resume` / `stop`: controls step streaming.

## Generated data
- `logs/simulationN.json`: object with `steps` (list of steps) and `summary` (aggregated).
- `logs/summaryN.json`: run summary for quick review.

## Configuration and settings
- `app/config.py` contains `SimulationSettings` (number of steps, tick, host/port, log paths, `verbose`).
- `app/world_config.json` and the files under `app/species/` define the world and species parameters.

## Requirements
- Python >= 3.12
- UV (Astral) — environment management and execution tool (usage documented in `simulatorV1/python_backend/README.md`).
- `websockets >= 15.0.1` for WebSocket communication.

## Running locally (with `uv` — recommended)

1. Lock then sync the dependencies via `uv`:

```powershell
uv lock
uv sync
```

2. Add a dependency (e.g. websockets):

```powershell
uv add websockets
```

3. Start the WebSocket server:

```powershell
# from simulatorV1/python_backend
uv run server.py
```

4. Run the offline CLI simulation:

```powershell
uv run app/main.py
```

Note: the `uv run` commands match the instructions in `simulatorV1/python_backend/README.md`.

## Debugging and logs
- The backend configures the global logger at DEBUG; detailed simulation log output is controlled by `SimulationSettings.verbose`.
- To clean up the logs:

```powershell
python -m simulatorV1.python_backend.scripts.clear_logs
```

## Development tips
- Respect the `domain` / `simulation` / `infrastructure` separation to ease unit testing.
- Add targeted tests for the rules in `simulation/` (movement, resource consumption).

## Useful resources
- Important files: [simulatorV1/python_backend/README.md](simulatorV1/python_backend/README.md), [simulatorV1/python_backend/REFERENCE.md](simulatorV1/python_backend/REFERENCE.md), [simulatorV1/python_backend/main.py](simulatorV1/python_backend/main.py), [simulatorV1/python_backend/server.py](simulatorV1/python_backend/server.py), [simulatorV1/godot_interface/simulation/scripts/socket_client.gd](simulatorV1/godot_interface/simulation/scripts/socket_client.gd)
