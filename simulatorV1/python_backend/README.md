# Python Backend Server

## Project Description
Ce backend Python alimente la simulation ecologique commandee par le client Godot. Il expose un serveur WebSocket bidirectionnel qui recoit des commandes, calcule les evolutions d'etat puis renvoie les mises a jour en temps reel.

## Requirements
- Python >= 3.12
- [UV (Astral)](https://docs.astral.sh/uv/getting-started/installation/) pour la gestion des dependances et l'execution.

## Installation
1. Installer UV (voir la documentation officielle ci-dessus).
2. Verrouiller les dependances :
   ```bash
   uv lock
   ```
3. Synchroniser l'environnement :
   ```bash
   uv sync
   ```

## Lancer les composants
- Serveur WebSocket :
  ```bash
  uv run server.py
  ```
  (le fichier `server.py` redirige vers `infrastructure/http/server.py`).
- Simulation CLI hors ligne :
  ```bash
  uv run app/main.py
  ```

## Architecture du package `python_backend`
```
python_backend/
|- app/                      # Point d'entree CLI et configuration
|- domain/                   # Modele metier (World, Species)
|- infrastructure/
|  |- http/                 # Serveur WebSocket
|  |- persistence/          # Ecriture des journaux JSON
|- scripts/                  # Utilitaires (ex. suppression des logs)
|- simulation/               # Moteur de simulation modularise
|- tests/                    # Emplacement pour les tests automatises
```

Les modules principaux :
- `simulation/engine.py` orchestre la boucle et s'appuie sur `simulation/animal.py`, `simulation/relationships.py`, `simulation/actions/*`, `simulation/action_executor.py` et `simulation/step_context.py`.
- `domain/` porte les entites pures (aucune dependance sur l'infrastructure).
- `infrastructure/persistence/log_writer.py` centralise l'ecriture des fichiers JSON lorsque l'option `write_logs` est activee.

Chaque execution journalisee genere un dossier logX/ contenant les fichiers principaux (`simulation.json`, `summary.json`) ainsi que quatre sous-dossiers (`animals/`, `groups/`, `species/`, `diets/`) offrant des historiques filtres par individu, groupe, espece ou regime alimentaire.

## Dependances
- **websockets >= 15.0.1** pour la communication temps reel.

Ajouter un package :
```bash
uv add <package_name>
```

## Interface Godot
Lancer le projet Godot contenu dans le dossier `godot_interface` pour consommer ce backend.
