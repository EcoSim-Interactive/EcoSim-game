import os
import shutil
import subprocess

# ================= CONFIGURATION =================
# 1. Chemin Godot 
GODOT_EXE = r'C:\Users\bouzi\Desktop\Programme sans installation\Godot_v4.5-stable_win64.exe\Godot_v4.5-stable_win64.exe'

# 2. Preset
EXPORT_PRESET = "Windows Desktop"

# 3. Chemins des fichiers
PROJECT_PATH = "./godot_interface/simulation/project.godot"
SERVER_SCRIPT = "./python_backend/server.py"
BUILD_DIR = os.path.abspath("./dist_final")

# 4. CONFIGURATION UV (Spécial dossier python_backend)
# On va chercher directement l'exécutable Python du venv
VENV_PYTHON = os.path.abspath(r"./python_backend/.venv/Scripts/python.exe")
# =================================================

def run_cmd(cmd):
    print(f"[CMD] {cmd}")
    try:
        subprocess.run(cmd, check=True, shell=True)
    except subprocess.CalledProcessError:
        print(f"ERREUR CRITIQUE sur la commande : {cmd}")
        exit(1)


def copy_resources(src, dst):
    """
    Copie TOUT le dossier src vers dst, mais ignore :
    - Les fichiers .py (le code est déjà dans l'exe)
    - Le dossier .venv (trop lourd et inutile)
    - Les caches (__pycache__)
    - Les fichiers spec temporaires
    """
    print(f">>> Copie des ressources de {src} vers {dst}...")
    
    # On définit ce qu'on NE VEUT PAS copier
    ignore_func = shutil.ignore_patterns(
        "*.py",             # Pas le code source
        "*.spec",           # Pas les fichiers de build
        ".venv",            # Pas l'environnement virtuel
        "__pycache__",      # Pas le cache python
        ".git",             # Pas le dossier git
        "*.exe"             # Pas les exe s'il y en a déjà
    )
    
    # dirs_exist_ok=True permet de fusionner si le dossier existe déjà
    shutil.copytree(src, dst, ignore=ignore_func, dirs_exist_ok=True)

def main():
    print("=== DÉBUT DE LA CONSTRUCTION (Mode UV Backend) ===")

    # Vérification que le Python du venv existe
    if not os.path.exists(VENV_PYTHON):
        print(f"ERREUR FATALE : Impossible de trouver le Python du venv ici :")
        print(f"{VENV_PYTHON}")
        print("Avez-vous bien fait 'uv sync' ou 'uv add pyinstaller' dans le dossier python_backend ?")
        exit(1)

    # 1. Nettoyage
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    
    os.makedirs(os.path.join(BUILD_DIR, "data"), exist_ok=True)

    backend_dir = os.path.dirname(SERVER_SCRIPT)
    server_dist_parent = os.path.join(BUILD_DIR, "data")
    
    cmd_server = (
            f'"{VENV_PYTHON}" -m PyInstaller '
            f'--onedir  '                 
            f'--contents-directory "." '  
            f'--hidden-import websockets '
            f'--collect-all websockets '
            f'--distpath "{server_dist_parent}" ' 
            f'--workpath "./temp/server" '
            f'--specpath "./temp" '
            f'--paths "{backend_dir}" ' 
            f'--name "server" '
            f'"{SERVER_SCRIPT}"'
        )
    run_cmd(cmd_server)

    final_server_dir = os.path.join(server_dist_parent, "server")
    print(f"\n>>> Copie des assets vers {final_server_dir}...")
    backend_source_dir = os.path.dirname(SERVER_SCRIPT)
    copy_resources(backend_source_dir, final_server_dir)

    # 3. Export du JEU Godot
    print("\n>>> Exportation de Godot Interface...")
    game_output = os.path.join(BUILD_DIR, "data", "game.exe")
    project_dir = os.path.dirname(PROJECT_PATH)
    
    cmd_godot = (
        f'"{GODOT_EXE}" --headless '
        f'--path "{project_dir}" '
        f'--export-release "{EXPORT_PRESET}" '
        f'"{game_output}"'
    )
    run_cmd(cmd_godot)

    # 4. Compilation du LANCEUR

    ICON_PATH = os.path.abspath("./assets/app_icon.ico") 
    
    # Vérification pour éviter que ça plante si l'icône n'existe pas
    icon_cmd = f'--icon "{ICON_PATH}" ' if os.path.exists(ICON_PATH) else ""

    print("\n>>> Compilation du Lanceur global...")
    cmd_launcher = (
        f'"{VENV_PYTHON}" -m PyInstaller  --onefile  '
        f'{icon_cmd}'
        f'--distpath "{BUILD_DIR}" '
        f'--workpath "./temp/launcher" '
        f'--specpath "./temp" '
        f'--name "EcoSim_Interactive" '
        f'launcher.py'
    )
    run_cmd(cmd_launcher)

    # 5. Nettoyage final
    if os.path.exists("./temp"):
        shutil.rmtree("./temp")

    print("\n=======================================")
    print(f"SUCCÈS ! Jeu prêt dans : {BUILD_DIR}")
    print("=======================================")

if __name__ == "__main__":
    main()