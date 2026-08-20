# Godot Frontend — `godot_interface`

This is the Godot 4 client of EcoSim Interactive. It connects to the
Python backend over WebSocket, drives the pre-computation and streaming
of a simulation run, and renders the world, animals, and resources in
real time. For the overall system architecture (backend + frontend +
WebSocket protocol), see [../../ARCHITECTURE.md](../../ARCHITECTURE.md)
and [../../docs/TECHNIQUE.md](../../docs/TECHNIQUE.md).

## Opening the project

Open `simulation/project.godot` in the Godot editor (version as declared
in that file) and run the `main` scene. The Python backend must be
running first — see
[../python_backend/README.md](../python_backend/README.md).

## Layout

```
godot_interface/simulation/
|- screens/       # Top-level scenes (Homepage, World, SpeciesCard, GraphCard, main)
|- scripts/        # GDScript logic, one script per scene/component
|- data/           # Local JSON data (species config, saved selections, ...)
|- Tilesets/        # Tilemap resources for the terrain
|- sprites/, spirites/, background/  # Visual assets
|- audio/          # Sound assets
|- shaders/        # Custom shaders (e.g. day/night tint)
|- UI/              # UI theme/assets
```

## Scenes

- **`screens/main.tscn`** — application root scene.
- **`screens/Homepage.tscn`** — home screen: import/start a run, live log
  display.
- **`screens/World.tscn`** — the simulation viewport: terrain, animals,
  food/water markers, camera.
- **`screens/SpeciesCard.tscn`** — per-species detail panel (stats,
  actions).
- **`screens/GraphCard.tscn`** — reusable chart widget (line/multi-line/
  bar) used to plot simulation metrics.

## Scripts (`simulation/scripts/`)

| Script | Role |
| --- | --- |
| `socket_client.gd` | Coordinates the WebSocket communication with the backend and the scene updates. Central hub: sends `get_world`, `compute`, `start`, `pause`, `resume`, `stop`; emits signals consumed by the rest of the UI on `step`, `status`, `summary`, `food_event`, etc. |
| `homepage.gd` | Controls the home screen and the progressive display of simulation logs. |
| `world_configurator.gd` | Species configuration modal shown before starting the simulation. |
| `compute_button.gd` | Button that triggers the simulation pre-computation via the network manager. |
| `startpausebutton.gd` | Synchronizes the button state with the simulation's start or pause. |
| `import_simulation.gd` / `FileDialog.gd` | Opens the file selection window and imports an existing JSON simulation run. |
| `camera_world.gd` | Manages the world camera's movement with drag, inertia and zoom. |
| `mini_world_preview.gd` | Displays a thumbnail of the world's terrain and allows picking a position by clicking on it. |
| `world_tint.gd` / `toggle_day_night.gd` | Manage the world's global tint and the day/night display of the simulated time. |
| `species_marker.gd` | Draws a minimalist marker to represent a species/animal on the map and handles its interaction. |
| `species_card.gd` | Controls the display panel showing detailed statistics for a selected species. |
| `food_marker.gd` | Displays a food resource with its visual rendering and remaining gauge. |
| `animal.gd` | Plays an animal's base animation when it appears. |
| `graph_card.gd` | UI card displaying a chart (single line, multi-line, or bars) from numeric data series. |
| `zoom_menu_button_homepage.gd` | Provides a simple zoom menu to control the camera from the UI. |

Every script carries a `##` doc comment above its `extends` declaration
and above each function, describing its role — read those first when
navigating the code.

## Client/server flow

1. `socket_client.gd` connects and sends `get_world`; the backend returns
   world geometry and resource lists, rendered by `World.tscn` via the
   marker scripts (`species_marker.gd`, `food_marker.gd`).
2. The user configures species in `world_configurator.gd`, then
   `compute_button.gd` sends `compute` to pre-compute the run.
3. `startpausebutton.gd` sends `start`/`pause`/`resume`/`stop`;
   `socket_client.gd` applies each incoming `step` payload to the scene,
   removing consumed resources on `food_event`.
4. `homepage.gd` and `graph_card.gd`/`species_card.gd` present logs and
   aggregate statistics from the `summary` frame at the end of a run.
