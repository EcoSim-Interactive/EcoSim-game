# Useful Commands Guide (Python Backend)

All these commands should be run from the root folder of the backend project (`python_backend`) using **`uv`**.

---

## Execution

| Command | Role | Description |
| :--- | :--- | :--- |
| **`uv run server.py`** | **Start the server** | Starts the WebSocket server (`ws://localhost:8765`) required to communicate in real time with the **Godot** interface. |
| **`uv run main.py`** | **CLI Simulation** | Runs an offline simulation (local console only). |
| **`uv run scripts/clear_logs.py`** | **Clean up logs** | Recursively deletes all `logs/` folders generated under the workspace to free up space. |

### Useful options for the CLI simulation (`uv run main.py`):
You can add flags to the local simulation command:
* **`--steps <N>`**: Changes the number of steps to run (e.g. `--steps 5000`).
* **`--write-logs`**: Writes detailed JSON files to `logs/logX/` (very useful for analyzing species life data).
* **`--verbose`**: Displays details of each step in your console.
* **`--seed <N>`**: Fixes the randomness to make the simulation 100% reproducible (e.g. `--seed 42`).
* **`--world-config <path>`**: Uses an alternative configuration file.

*Full command example:*
```bash
uv run main.py --steps 5000 --write-logs --seed 42
```

---

## Tests and Quality

| Command | Role | Description |
| :--- | :--- | :--- |
| **`uv run python -m unittest discover tests`** | **Unit Tests** | Runs the entire automated test suite (checks AI behavior, movement, etc.). |
| **`uv run ruff check .`** | **Linter** | Analyzes the code for potential bugs or Python rule violations. |
| **`uv run ruff check --fix .`** | **Autocorrect** | Automatically fixes most small code issues detected by the linter. |
| **`uv run ruff format .`** | **Formatting** | Neatly reformats all your code to comply with PEP 8 style standards. |

---

## Project Management

| Command | Role | Description |
| :--- | :--- | :--- |
| **`uv lock`** | **Locking** | Updates the `uv.lock` file to lock exact dependency versions. |
| **`uv sync`** | **Sync** | Installs or syncs the virtual environment (`.venv`) so the application is ready. |
| **`uv add <package_name>`** | **Add dependency** | Installs a new third-party library (e.g. `uv add requests`). |
