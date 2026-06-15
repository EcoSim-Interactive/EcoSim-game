import subprocess
import time
import os
import sys
import platform

def main():
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    system = platform.system()
    
    
    ext = ".exe" if system == "Windows" else ""
    
    server_exe = os.path.join(base_dir, "data", "server", f"server{ext}")
    
    
    if system == "Windows":
        game_name = "game.exe"
    elif system == "Darwin": 
        game_name = "game.app/Contents/MacOS/game" 
    else: 
        game_name = "game.x86_64"

    game_exe = os.path.join(base_dir, "data", game_name)

    if not os.path.exists(server_exe) or not os.path.exists(game_exe):
        print(f"Erreur : Impossible de trouver {game_name} ou server{ext}")
        return

    print("--- Démarrage ---")

    
    server_process = subprocess.Popen([server_exe], cwd=os.path.dirname(server_exe))
    time.sleep(0.5) 

    
    try:
        subprocess.run([game_exe], check=False)
    except Exception as e:
        print(f"Erreur lancement jeu : {e}")

    
    print("Arrêt du serveur...")
    server_process.terminate()
    server_process.wait()

if __name__ == "__main__":
    main()