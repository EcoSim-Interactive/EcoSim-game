# Guide des Commandes Utiles (Backend Python)

Toutes ces commandes doivent être exécutées depuis le dossier racine du projet backend (`python_backend`) à l'aide de **`uv`**.

---

## Exécution

| Commande | Rôle | Description |
| :--- | :--- | :--- |
| **`uv run server.py`** | **Lancement du serveur** | Démarre le serveur WebSocket (`ws://localhost:8765`) requis pour communiquer en temps réel avec l'interface **Godot**. |
| **`uv run main.py`** | **Simulation CLI** | Lance une simulation hors-ligne (en local console uniquement). |
| **`uv run scripts/clear_logs.py`** | **Nettoyage des logs** | Supprime récursivement tous les dossiers de journaux `logs/` générés sous l'espace de travail pour libérer de l'espace. |

### Options utiles pour la simulation CLI (`uv run main.py`) :
Vous pouvez ajouter des drapeaux (flags) à la commande de simulation locale :
* **`--steps <N>`** : Modifie le nombre d'étapes à exécuter (ex: `--steps 5000`).
* **`--write-logs`** : Écrit les fichiers JSON détaillés dans `logs/logX/` (très utile pour analyser les données de vie des espèces).
* **`--verbose`** : Affiche les détails de chaque étape dans votre console.
* **`--seed <N>`** : Fixe l'aléa pour rendre la simulation 100% reproductible (ex: `--seed 42`).
* **`--world-config <chemin>`** : Utilise un fichier de configuration alternatif.

*Exemple de commande complète :*
```bash
uv run main.py --steps 5000 --write-logs --seed 42
```

---

## Tests et Qualité

| Commande | Rôle | Description |
| :--- | :--- | :--- |
| **`uv run python -m unittest discover tests`** | **Tests Unitaires** | Exécute l'ensemble de la suite de tests automatisés (vérifie les comportements IA, déplacement, etc.). |
| **`uv run ruff check .`** | **Linter** | Analyse le code à la recherche de bugs potentiels ou de non-respect des règles Python. |
| **`uv run ruff check --fix .`** | **Autocorrect** | Corrige automatiquement la plupart des petits défauts de code détectés par le Linter. |
| **`uv run ruff format .`** | **Formatage** | Remet en page tout votre code proprement pour respecter les normes de style PEP 8. |

---

## Gestion du projet

| Commande | Rôle | Description |
| :--- | :--- | :--- |
| **`uv lock`** | **Verrouillage** | Met à jour le fichier `uv.lock` pour verrouiller les versions exactes des dépendances. |
| **`uv sync`** | **Synchronisation** | Installe ou synchronise l'environnement virtuel (`.venv`) pour que l'application soit prête. |
| **`uv add <nom_du_package>`** | **Ajout dépendance** | Installe une nouvelle librairie tierce (ex: `uv add requests`). |
