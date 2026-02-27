# Project Architecture

This document describes the structure of **simulatorV1** and explains how the main pieces interact to deliver a precomputed step-by-step ecosystem simulation streamed over WebSocket to the Godot front-end.

## Overview

- **Python backend** (`simulatorV1/python_backend`): simulation core and WebSocket server.
- **Godot interface** (`simulatorV1/godot_interface`): runtime visualisation and controls.
- **Simulation logs** (`simulatorV1/python_backend/logs`): JSON dumps generated for each run (cached steps + summary).

Typical flow:
1. The client asks the backend to build the world (`get_world`).
2. The backend precomputes all steps on demand (`compute`).
3. The client streams computed steps one by one (`start`, `pause`, `resume`, `stop`).

## Backend layout

```
simulatorV1/python_backend
??? app            # configuration & CLI entry point
??? domain         # domain models (World, Species)
??? infrastructure # persistence & network adapters
??? simulation     # simulation engine and behaviour bricks
??? scripts        # utilities (log cleanup, etc.)
??? server.py      # thin wrapper that runs the WebSocket server
```

### `app`
- `app/config.py` defines `SimulationSettings` (steps, tick, host/port, log paths, `verbose`).
- `app/main.py` is a CLI that instantiates a default world, runs the simulation with `SimulationEngine` and logs the JSON summary.

### `domain`
- `domain/world.py` builds the map (size, minutes per step) and stores food/water sources.
- `domain/species.py` models each creature (position, senses, vital needs, behaviour helpers like move, rest, eat, drink).

### `simulation`
- `simulation/engine.py` orchestrates each step and now caches the full run:
  - `generate_all_steps()` runs the timeline once, keeps it in memory and writes `simulationN.json` plus `summaryN.json` when logging is enabled.
  - `save_summary()` exposes an aggregate snapshot at the end of a run.
- `behaviors.py` and `action_executor.py` contain the decision rules (thirst, hunger, fatigue, idle) and post-action resolution (check if food was eaten).
- `step_context.py` builds per-step payloads (`before`/`after` state, time metadata) and the final summary payload.
- `event_log.py` proxies verbosity through Python's `logging` module so global settings drive all diagnostics.

### `infrastructure`
- `http/server.py` exposes the WebSocket API (powered by `websockets`). Responsibilities:
  - create the world (`get_world`), using `SimulationSettings` to seed defaults;
  - precompute steps in a background task (`_compute_steps`) using `asyncio.to_thread` to keep the event loop responsive;
  - stream cached steps via `simulation_runner`, controlled by `pause_event`, `stop_event` and `step_cursor`;
  - emit structured status frames (`status`, `error`, `summary`) so clients can react quickly;
  - manage persistent run metadata (`steps_file`, `summary_file`).
- `persistence/log_writer.py` chooses the next run index and writes `simulationN.json` (steps array + optional summary) and `summaryN.json` for quick lookup.

### `scripts`
- `scripts/clear_logs.py` removes every `logs` directory from the workspace and reports deletions through the shared logger.

## WebSocket runtime flow

1. **Startup**: `uv run server.py` (or `python -m infrastructure.http.server`). Each entry point executes `logging.basicConfig(level=logging.DEBUG, force=True)` so uv's defaults cannot hide messages.
2. **Handshake**: the Godot client connects, sends `get_world`, and receives initial world geometry plus resource lists.
3. **Precomputation**: the client sends `compute`; `_compute_steps` calls `SimulationEngine.generate_all_steps()` and `save_summary()`, caching results and optionally persisting them.
4. **Streaming**: `start` triggers `simulation_runner`, which pushes one cached step every `tick_ms` milliseconds and honours `pause`, `resume`, and `stop` commands.
5. **Closure**: when all steps are emitted, a `summary` frame finalises the run; cached files remain for offline inspection.

## Godot interface

Located under `simulatorV1/godot_interface`:
- `simulation/scripts/socket_client.gd` manages the WebSocket connection, forwards user commands (`start`, `pause`, `resume`, `stop`, `compute`) and updates the scene graph on each `step` payload.
- `simulation/scripts/startpausebutton.gd` and `simulation/scripts/compute_button.gd` wire UI controls to the socket client.

The client mirrors the backend command set and removes eaten resources from the scene when notified (`food_event`).

## Logging strategy

- Every backend entry point configures `logging` in DEBUG with `force=True` to keep behaviour identical whether commands run through `uv` or plain Python.
- `SimulationSettings.verbose` still governs in-engine log emission; when `False`, `EventLogger` remains quiet even though the global logger is ready.

## Generated data

- `logs/simulationN.json` contains `{ "steps": [...], "summary": {...} }` for each run.
- `logs/summaryN.json` mirrors the summary for quick consumption.
- Legacy `stepX.json` files can be removed via `python -m simulatorV1.python_backend.scripts.clear_logs`.

## Execution shortcuts

```bash
# WebSocket server
uv run server.py

# Offline CLI simulation
uv run main.py
```
