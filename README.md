# EcoSim Interactive (SimulatorV1)

EcoSim Interactive is an ecosystem-simulation project pairing a
precomputed, step-by-step Python simulation engine with a Godot
front-end for real-time visualization and control.

## Overview

- **Python backend** (`simulatorV1/python_backend`) — simulation engine
  and WebSocket server. It precomputes every step of a run, then streams
  the cached steps to the client on request.
- **Godot interface** (`simulatorV1/godot_interface`) — visualization and
  runtime controls (start/pause/resume/stop, species and world
  configuration).
- **Showcase website** (`site-vitrine`) — React/Vite front-end presenting
  the project.

## Documentation

| Document | Purpose |
| --- | --- |
| [fiche_projet.md](fiche_projet.md) | Project brief: team, target audience, positioning, tech stack. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the backend and Godot client are structured and interact. |
| [docs/TECHNIQUE.md](docs/TECHNIQUE.md) | Technical documentation: setup, execution, WebSocket API, logging. |
| [docs/NON_TECHNIQUE.md](docs/NON_TECHNIQUE.md) | Non-technical summary for end users. |
| [simulatorV1/python_backend/README.md](simulatorV1/python_backend/README.md) | Backend install/run/test instructions. |
| [simulatorV1/python_backend/REFERENCE.md](simulatorV1/python_backend/REFERENCE.md) | Module-by-module API reference (generated from the code's docstrings). |
| [simulatorV1/python_backend/commande.md](simulatorV1/python_backend/commande.md) | Quick command cheat sheet for the backend. |

## Quick start

1. Start the Python backend (see
   [simulatorV1/python_backend/README.md](simulatorV1/python_backend/README.md)
   for prerequisites):
   ```bash
   cd simulatorV1/python_backend
   uv sync
   uv run server.py
   ```
2. Open the Godot project at
   `simulatorV1/godot_interface/simulation` in the Godot editor and run
   it.
3. In the Godot interface, click **Compute** to precompute a run, then
   **Start** to stream the simulation step by step.

## Requirements

- Python >= 3.12 and [uv (Astral)](https://docs.astral.sh/uv/getting-started/installation/)
- Godot (version defined in
  `simulatorV1/godot_interface/simulation/project.godot`)

## Project status

Active development — see [fiche_projet.md](fiche_projet.md) for the
team and roadmap.
