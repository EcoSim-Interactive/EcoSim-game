import os
import shutil
import subprocess
import sys
import platform

# ================= CONFIGURATION =================
PROJECT_PATH = "./godot_interface/simulation/project.godot"
SERVER_SCRIPT = "./python_backend/server.py"
BUILD_DIR = os.path.abspath("./dist_final")

# Détection de l'OS
SYSTEM = platform.system()
IS_WIN = SYSTEM == "Windows"
EXT = ".exe" if IS_WIN else ""

# Presets attendus dans project.godot (export_presets.cfg)
PRESETS = {
    "Windows": "Windows Desktop",
    "Linux": "Linux",
    "Darwin": "macOS"
}
EXPORT_PRESET = PRESETS.get(SYSTEM, "Linux/X11")

GAME_OUTPUTS = {
    "Windows": "game.exe",
    "Linux": "game.x86_64",
    "Darwin": "game.zip" # MacOS exporte souvent en zip ou .app
}
GAME_OUTPUT_NAME = GAME_OUTPUTS.get(SYSTEM, "game.x86_64")
# =================================================

def run_cmd(cmd):
    print(f"[CMD] {cmd}")
    try:
        subprocess.run(cmd, check=True, shell=True)
    except subprocess.CalledProcessError:
        print(f"ERREUR CRITIQUE sur la commande : {cmd}")
        exit(1)

def copy_resources(src, dst):
    ignore_func = shutil.ignore_patterns("*.py", "*.spec", ".venv", "__pycache__", ".git")
    shutil.copytree(src, dst, ignore=ignore_func, dirs_exist_ok=True)

def main():
    print(f"=== CONSTRUCTION POUR {SYSTEM} ===")

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(os.path.join(BUILD_DIR, "data"), exist_ok=True)

    # 1. Compilation du Serveur (PyInstaller via UV)
    # Dans la CI, 'uv run' s'assure d'utiliser l'environnement correctement
    backend_dir = os.path.dirname(SERVER_SCRIPT)
    server_dist_parent = os.path.join(BUILD_DIR, "data")
    
    cmd_server = (
        f'uv run pyinstaller --onedir --contents-directory "." '
        f'--hidden-import websockets --collect-all websockets '
        f'--distpath "{server_dist_parent}" --workpath "./temp/server" '
        f'--specpath "./temp" --paths "{backend_dir}" --name "server" "{SERVER_SCRIPT}"'
    )
    run_cmd(cmd_server)
    copy_resources(backend_dir, os.path.join(server_dist_parent, "server"))

    # 2. Export Godot (utilise l'exécutable 'godot' injecté par la CI)
    game_output = os.path.join(BUILD_DIR, "data", GAME_OUTPUT_NAME)
    project_dir = os.path.dirname(PROJECT_PATH)
    cmd_godot = f'godot --headless --path "{project_dir}" --export-release "{EXPORT_PRESET}" "{game_output}"'
    run_cmd(cmd_godot)

    # 3. Compilation du Launcher
    icon_path = os.path.abspath("./assets/app_icon.ico")
    icon_cmd = f'--icon "{icon_path}" ' if os.path.exists(icon_path) and IS_WIN else ""

    cmd_launcher = (
        f'uv run pyinstaller --onefile {icon_cmd}'
        f'--distpath "{BUILD_DIR}" --workpath "./temp/launcher" '
        f'--specpath "./temp" --name "EcoSim_Interactive" launcher.py'
    )
    run_cmd(cmd_launcher)

    if os.path.exists("./temp"):
        shutil.rmtree("./temp")
    print(f"SUCCÈS ! Jeu prêt dans : {BUILD_DIR}")

if __name__ == "__main__":
    main()