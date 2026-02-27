import subprocess
import time
import os
import sys

def main():
    # Ce script sera transformé en .exe, donc on récupère son propre dossier
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Chemins relatifs à l'intérieur du dossier construit
    server_exe = os.path.join(base_dir, "data", "server", "server.exe")
    game_exe = os.path.join(base_dir, "data", "game.exe")

    # Vérification de sécurité
    if not os.path.exists(server_exe) or not os.path.exists(game_exe):
        print("Erreur : Impossible de trouver game.exe ou server.exe")
        print(f"Cherché ici : {server_exe}")
        input("Appuyez sur Entrée...")
        return

    print("--- Démarrage ---")

    # 1. Lancer le SERVEUR
    server_process = subprocess.Popen([server_exe], cwd=os.path.dirname(server_exe))

    # Pause courte pour laisser le serveur s'allumer
    time.sleep(0.5) 

    # 2. Lancer GODOT (Bloquant)
    try:
        subprocess.run([game_exe], check=False)
    except Exception as e:
        print(f"Erreur lancement jeu : {e}")

    # 3. Tuer le SERVEUR quand Godot est fermé
    print("Arrêt du serveur...")
    subprocess.call(['taskkill', '/F', '/T', '/PID', str(server_process.pid)])

if __name__ == "__main__":
    main()