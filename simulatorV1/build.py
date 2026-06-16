import os
import shutil
import subprocess
import sys
import platform

# ================= CONFIGURATION =================
# On est DÉJÀ dans simulatorV1 au moment où le script tourne.
PROJECT_PATH = "./godot_interface/simulation/project.godot"
SERVER_SCRIPT = "./python_backend/server.py"
BUILD_DIR = os.path.abspath("./dist_final")

# RUSTINE BASH : On remplace les "\" par des "/" pour que Bash les lise correctement
GODOT_BIN = os.environ.get("GODOT", "godot").replace("\\", "/")

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
EXPORT_PRESET = PRESETS.get(SYSTEM, "Linux")

GAME_OUTPUTS = {
    "Windows": "game.exe",
    "Linux": "game.x86_64",
    "Darwin": "game.zip"
}
GAME_OUTPUT_NAME = GAME_OUTPUTS.get(SYSTEM, "game.x86_64")

# MAGIE MULTIPLATEFORME : On cible directement le bon exécutable du Venv
VENV_BIN = "Scripts" if IS_WIN else "bin"
VENV_PYTHON = os.path.abspath(f"./python_backend/.venv/{VENV_BIN}/python{EXT}")
# =================================================

def run_cmd(cmd, force_bash=False):
    print(f"[CMD] {cmd}")
    try:
        if force_bash and IS_WIN:
            git_bash_path = r"C:\Program Files\Git\bin\bash.exe"
            
            if os.path.exists(git_bash_path):
                subprocess.run([git_bash_path, "-c", cmd], check=True)
            else:
                subprocess.run(["sh", "-c", cmd], check=True)
        else:
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

    # 1. Compilation du Serveur avec le VENV direct
    backend_dir = os.path.dirname(SERVER_SCRIPT)
    server_dist_parent = os.path.join(BUILD_DIR, "data")
    
    cmd_server = (
        f'"{VENV_PYTHON}" -m PyInstaller --onedir --contents-directory "." '
        f'--hidden-import websockets --collect-all websockets '
        f'--distpath "{server_dist_parent}" --workpath "./temp/server" '
        f'--specpath "./temp" --paths "{backend_dir}" --name "server" "{SERVER_SCRIPT}"'
    )
    run_cmd(cmd_server)
    copy_resources(backend_dir, os.path.join(server_dist_parent, "server"))

    # 2. Export Godot (Formaté avec des / pour Bash)
    game_output = os.path.join(BUILD_DIR, "data", GAME_OUTPUT_NAME).replace("\\", "/")
    project_dir = os.path.dirname(PROJECT_PATH).replace("\\", "/")
    
    cmd_godot = f'"{GODOT_BIN}" --headless --path "{project_dir}" --export-release "{EXPORT_PRESET}" "{game_output}"'
    
    # LA MAGIE EST ICI : On passe force_bash=True pour contourner cmd.exe sur Windows
    run_cmd(cmd_godot, force_bash=True)

    # 3. Compilation du Launcher avec le VENV direct
    icon_path = os.path.abspath("./assets/app_icon.ico")
    icon_cmd = f'--icon "{icon_path}" ' if os.path.exists(icon_path) and IS_WIN else ""

    cmd_launcher = (
        f'"{VENV_PYTHON}" -m PyInstaller --onefile {icon_cmd}'
        f'--distpath "{BUILD_DIR}" --workpath "./temp/launcher" '
        f'--specpath "./temp" --name "EcoSim_Interactive" launcher.py'
    )
    run_cmd(cmd_launcher)

    if os.path.exists("./temp"):
        shutil.rmtree("./temp")
    print(f"SUCCÈS ! Jeu prêt dans : {BUILD_DIR}")

if __name__ == "__main__":
    main()