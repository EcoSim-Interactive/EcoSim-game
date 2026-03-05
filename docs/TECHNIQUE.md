# Documentation Technique

## Objectif
Ce dépôt contient un simulateur d'écosystème pré-calculé (backend Python) et une interface Godot pour la visualisation et le contrôle en temps réel.

## Arborescence essentielle
- `simulatorV1/python_backend` : moteur de simulation, API WebSocket et utilitaires.
- `simulatorV1/godot_interface/simulation` : projet Godot (scènes + scripts client WebSocket).
- `simulatorV1/python_backend/logs` : sorties JSON (`simulationN.json`, `summaryN.json`).

## Architecture générale

- Backend Python
  - `app/` : points d'entrée CLI et configuration (`SimulationSettings`).
  - `domain/` : modèles du domaine (monde, espèces, ressources).
  - `simulation/` : moteur (`engine.py`), exécution d'actions, génération d'étapes et contexte de step.
  - `infrastructure/http` : serveur WebSocket (gestion des commandes client, streaming des steps).
  - `infrastructure/persistence` : écriture des logs et gestion des fichiers de run.

- Frontend Godot
  - `socket_client.gd` envoie `get_world`, `compute`, `start`, `pause`, `resume`, `stop` et reçoit les payloads `step`, `status`, `summary`.

## Flux runtime (résumé)
1. Client envoie `get_world` → backend renvoie géométrie + ressources.
2. Client demande `compute` → backend exécute `SimulationEngine.generate_all_steps()` (pré-calcul en background) et produit les fichiers de log.
3. Client envoie `start` → backend stream un step toutes les `tick_ms` en respectant `pause`/`stop`.
4. À la fin, backend émet une trame `summary`.

## API WebSocket (commandes clés)
- `get_world` : construction et renvoi du monde initial.
- `compute` : démarre la pré-calcul des étapes (task en arrière-plan).
- `start` / `pause` / `resume` / `stop` : contrôle du streaming des steps.

## Données générées
- `logs/simulationN.json` : objet avec `steps` (liste d'étapes) et `summary` (agrégé).
- `logs/summaryN.json` : résumé de course pour consultation rapide.

## Configuration et paramètres
- `app/config.py` contient `SimulationSettings` (nombre d'étapes, tick, host/port, chemins logs, `verbose`).
- `app/world_config.json` et les fichiers dans `app/species/` définissent les paramètres du monde et des espèces.

## Prérequis
- Python >= 3.12
- UV (Astral) — outil de gestion d'env et d'exécution (usage documenté dans `simulatorV1/python_backend/README.md`).
- `websockets >= 15.0.1` pour la communication WebSocket.

## Exécution locale (avec `uv` — recommandé)

1. Verrouiller puis synchroniser les dépendances via `uv` :

```powershell
uv lock
uv sync
```

2. Ajouter une dépendance (ex. websockets) :

```powershell
uv add websockets
```

3. Lancer le serveur WebSocket :

```powershell
# depuis simulatorV1/python_backend
uv run server.py
```

4. Lancer la simulation CLI hors-ligne :

```powershell
uv run app/main.py
```

Remarque : les commandes `uv run` correspondent aux instructions présentes dans `simulatorV1/python_backend/README.md`.

## Débogage et logs
- Le backend configure le logger global en DEBUG; l'émission de logs détaillés de simulation est contrôlée par `SimulationSettings.verbose`.
- Pour nettoyer les logs :

```powershell
python -m simulatorV1.python_backend.scripts.clear_logs
```

## Conseils de développement
- Respectez la séparation `domain` / `simulation` / `infrastructure` pour faciliter les tests unitaires.
- Ajouter des tests ciblés pour les règles dans `simulation/` (déplacements, consommation de ressources).

## Ressources utiles
- Fichiers importants : [simulatorV1/python_backend/README.md](simulatorV1/python_backend/README.md), [simulatorV1/python_backend/main.py](simulatorV1/python_backend/main.py), [simulatorV1/python_backend/server.py](simulatorV1/python_backend/server.py), [simulatorV1/godot_interface/simulation/scripts/socket_client.gd](simulatorV1/godot_interface/simulation/scripts/socket_client.gd)

