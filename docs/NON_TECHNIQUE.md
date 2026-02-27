# Documentation Non-Technique (Résumé utilisateur)

## But du projet
Ce projet simule un écosystème numérique (animaux, nourriture, eau) et permet de visualiser la simulation dans un client Godot. L'objectif est d'expérimenter des comportements d'espèces et de visualiser l'évolution pas à pas.

## Public cible
- Enseignants et étudiants en simulation/IA
- Développeurs souhaitant étudier la modélisation d'écosystèmes
- Toute personne souhaitant visualiser des processus multi-agents

## Utilisation rapide
1. Ouvrir le projet Godot : `simulatorV1/godot_interface/simulation` dans l'éditeur Godot.
2. Lancer le backend Python (voir `docs/TECHNIQUE.md` pour l'installation).
3. Dans l'interface Godot, se connecter au serveur, cliquer sur `Compute` pour pré-calculer puis `Start` pour jouer la simulation pas à pas.

## Points clés à comprendre
- Le backend pré-calcule toutes les étapes (pour garantir reproductibilité et facilité d'inspection).
- Le client reçoit ensuite les étapes une à une et met à jour la scène (les ressources consommées disparaissent, etc.).
- Les runs sont sauvegardés dans `simulatorV1/python_backend/logs` pour revue hors-ligne.

## Fichiers importants (pour l'utilisateur)
- Projet Godot : [simulatorV1/godot_interface/simulation](simulatorV1/godot_interface/simulation)
- Backend (lancer et logs) : [simulatorV1/python_backend](simulatorV1/python_backend)

## Prochaines étapes recommandées
- Tester différents `world_config.json` et profils d'espèces pour observer l'impact.
- Exporter les logs et créer de courtes vidéos/gifs pour la présentation.

## Pourquoi ce projet est utile
- Pédagogie : permet d'illustrer des concepts de simulation multi-agents (besoins, ressources, interactions).
- Recherche & prototypage : plateforme simple pour tester heuristiques de comportement.
- Démonstration : produire des visualisations reproductibles (logs pré-calculés).

## Démonstration pas-à-pas (pour non-techniques)
1. Ouvrez l'éditeur Godot et chargez le projet situé dans `simulatorV1/godot_interface/simulation` (ouvrir `project.godot`).
2. Lancez le backend Python : ouvrez un terminal, placez-vous dans `simulatorV1/python_backend` et exécutez `uv run server.py` (voir `docs/TECHNIQUE.md` si nécessaire).
3. Dans l'interface Godot, configurez l'adresse/port si nécessaire, puis cliquez sur `Compute` pour pré-calculer le run.
4. Après que le calcul soit terminé, cliquez sur `Start` pour dérouler la simulation pas à pas. Utilisez `Pause` / `Resume` / `Stop` selon besoin.
5. Pour revoir un run hors-ligne, consultez le dossier `simulatorV1/python_backend/logs` et ouvrez le fichier `summaryN.json`.

## Exigences système (résumé)
- Système d'exploitation : Windows/Mac/Linux (Godot et Python disponibles sur ces plateformes).
- Python >= 3.12 et `uv` (Astral) pour gérer/exécuter l'environnement Python (instructions dans `simulatorV1/python_backend/README.md`).
- Godot (la version utilisée pour le projet est définie dans `simulatorV1/godot_interface/simulation/project.godot`).
- Ressources : simulation légère; une machine ordinaire (4+ GB RAM) suffit pour les démos courantes.

## Résultats attendus (ce que vous verrez)
- Une carte représentant le monde, des marqueurs pour nourriture et eau et des entités animales se déplaçant selon leurs besoins.
- Événements visibles : déplacement, consommation de nourriture/eau, repos, interactions simples entre individus.
- Les ressources consommées disparaîtront visuellement et les logs enregistreront l'état à chaque étape.

## FAQ & dépannage rapide
- Je ne peux pas me connecter depuis Godot → vérifiez host/port, assurez-vous que `uv run server.py` tourne et que le pare-feu autorise la connexion.
- `uv` introuvable → installez UV/Astral selon la documentation liée dans `simulatorV1/python_backend/README.md`.
- Pas de rendu ou scènes vides → ouvrir `World.tscn` et vérifier que la scène principale est chargée; regarder la console Godot pour erreurs.
- Logs manquants → vérifiez la configuration `write_logs` dans les paramètres de simulation et l'emplacement `simulatorV1/python_backend/logs`.

## Comment lire les logs (simple)
- `simulationN.json` contient la liste complète des étapes (`steps`) et un `summary` agrégé.
- `summaryN.json` donne un aperçu rapide (nombre d'animaux, ressources restantes, métriques globales).
- Ouvrez ces fichiers avec un éditeur de texte ou un visualiseur JSON pour parcourir les événements.

## Limites connues
- Pré-calcul simplifié : la simulation est conçue pour être reproductible et lisible, pas pour modéliser de façon réaliste tous comportements biologiques.
- Échelle et performance : des mondes très grands ou trop d'agents peuvent accroître la durée du pré-calcul et la taille des logs.

## Contribution et contact
- Pour proposer un changement : ouvrez une issue ou soumettez une pull request sur le dépôt.
- Pour questions rapides : indiquez dans l'issue un résumé, la version du projet et, si possible, un extrait de `summaryN.json` ou la capture d'écran.

## Visuels et export
- Pour des présentations, capturez la fenêtre Godot pendant la lecture et exportez un GIF/vidéo. Godot permet d'enregistrer des images successives ou d'utiliser un utilitaire externe pour capturer l'écran.

