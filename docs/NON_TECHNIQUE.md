# Non-Technical Documentation (User Summary)

## Project goal
This project simulates a digital ecosystem (animals, food, water) and lets you visualize the simulation in a Godot client. The goal is to experiment with species behaviors and watch the evolution unfold step by step.

## Target audience
- Teachers and students in simulation/AI
- Developers wanting to study ecosystem modeling
- Anyone wanting to visualize multi-agent processes

## Quick start
1. Open the Godot project: `simulatorV1/godot_interface/simulation` in the Godot editor.
2. Launch the Python backend (see `docs/TECHNIQUE.md` for installation).
3. In the Godot interface, connect to the server, click `Compute` to pre-calculate, then `Start` to play the simulation step by step.

## Key points to understand
- The backend pre-calculates all steps (to guarantee reproducibility and ease of inspection).
- The client then receives the steps one by one and updates the scene (consumed resources disappear, etc.).
- Runs are saved in `simulatorV1/python_backend/logs` for offline review.

## Important files (for the user)
- Godot project: [simulatorV1/godot_interface/simulation](simulatorV1/godot_interface/simulation)
- Backend (run and logs): [simulatorV1/python_backend](simulatorV1/python_backend)

## Recommended next steps
- Test different `world_config.json` files and species profiles to observe the impact.
- Export the logs and create short videos/gifs for the presentation.

## Why this project is useful
- Teaching: illustrates multi-agent simulation concepts (needs, resources, interactions).
- Research & prototyping: a simple platform for testing behavior heuristics.
- Demonstration: produces reproducible visualizations (pre-calculated logs).

## Step-by-step demo (for non-technical users)
1. Open the Godot editor and load the project located in `simulatorV1/godot_interface/simulation` (open `project.godot`).
2. Launch the Python backend: open a terminal, navigate to `simulatorV1/python_backend` and run `uv run server.py` (see `docs/TECHNIQUE.md` if needed).
3. In the Godot interface, configure the address/port if needed, then click `Compute` to pre-calculate the run.
4. Once the calculation is done, click `Start` to play the simulation step by step. Use `Pause` / `Resume` / `Stop` as needed.
5. To review a run offline, check the `simulatorV1/python_backend/logs` folder and open the `summaryN.json` file.

## System requirements (summary)
- Operating system: Windows/Mac/Linux (Godot and Python are available on these platforms).
- Python >= 3.12 and `uv` (Astral) to manage/run the Python environment (instructions in `simulatorV1/python_backend/README.md`).
- Godot (the version used for the project is defined in `simulatorV1/godot_interface/simulation/project.godot`).
- Resources: lightweight simulation; an ordinary machine (4+ GB RAM) is enough for typical demos.

## Expected results (what you will see)
- A map representing the world, markers for food and water, and animal entities moving according to their needs.
- Visible events: movement, consuming food/water, resting, simple interactions between individuals.
- Consumed resources will visually disappear and the logs will record the state at each step.

## FAQ & quick troubleshooting
- Can't connect from Godot -> check host/port, make sure `uv run server.py` is running and the firewall allows the connection.
- `uv` not found -> install UV/Astral following the documentation linked in `simulatorV1/python_backend/README.md`.
- No rendering or empty scenes -> open `World.tscn` and check that the main scene is loaded; check the Godot console for errors.
- Missing logs -> check the `write_logs` setting in the simulation parameters and the `simulatorV1/python_backend/logs` location.

## How to read the logs (simple)
- `simulationN.json` contains the full list of steps (`steps`) and an aggregated `summary`.
- `summaryN.json` gives a quick overview (number of animals, remaining resources, global metrics).
- Open these files with a text editor or a JSON viewer to browse the events.

## Known limitations
- Simplified pre-calculation: the simulation is designed to be reproducible and readable, not to realistically model all biological behaviors.
- Scale and performance: very large worlds or too many agents can increase pre-calculation time and log size.

## Contribution and contact
- To propose a change: open an issue or submit a pull request on the repository.
- For quick questions: include in the issue a summary, the project version and, if possible, an excerpt of `summaryN.json` or a screenshot.

## Visuals and export
- For presentations, capture the Godot window during playback and export a GIF/video. Godot lets you record successive frames or use an external utility to capture the screen.
