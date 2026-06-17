# Fiche Projet : EcoSim Interactive (SimulatorV1)

EcoSim Interactive est un logiciel de simulation d'écosystèmes offrant une expérience à la fois ludique et rigoureuse. Il permet de créer, d'observer et de manipuler des environnements complexes peuplés d'espèces qui interagissent selon des modèles écologiques réels.

## 1. Équipe du Projet

L'équipe est organisée autour des principales dimensions du projet :

- Thomas Boulard : Back-End et Moteur de Simulation. Responsable de la modélisation des interactions écologiques et des règles de l'écosystème.
- Nassim Bouziane : Back-End et Infrastructure & Systèmes. En charge du déploiement, de la sécurité de l'infrastructure et de la gestion des utilisateurs.
- Abdelqoudousse Boustani : Back-End et Données & Visualisation. S'occupe de la visualisation scientifique, ainsi que de la gestion, du traitement et de l'export des données.

## 2. Public Cible

- Éducation (cible principale) : Établissements scolaires, universités et centres de formation cherchant un outil d'apprentissage interactif.
- Recherche : Laboratoires et centres d’études environnementales pour tester des modèles écologiques.
- Grand Public : Passionnés de biodiversité et curieux du vivant.

## 3. Contextualisation et Problématique

Face à l’effondrement accéléré des écosystèmes, il devient urgent de mieux les comprendre pour mieux les protéger. Pourtant, les outils actuels de modélisation écologique sont souvent réservés aux spécialistes et peu engageants.

Problématique :
Comment transformer l’étude des interactions au sein d’un écosystème en une expérience plus intuitive, pédagogique et captivante, sans compromis sur la rigueur scientifique ?

Valeur Ajoutée :
- Interface intuitive : Accessible sans prérequis techniques approfondis.
- Simulation réaliste : Prise en compte d'interactions complexes telles que la prédation, le cycle des ressources et le métabolisme.
- Analyse de données : Export structuré (JSON/CSV) permettant un véritable usage scientifique et pédagogique.

## 4. Concurrence

- Concurrence directe : SimEarth (obsolète) et SimOïko (rigoureux mais manquant d'une interface intuitive).
- Concurrence indirecte : Tyto Ecology, The Sandbox et Universe Sandbox, qui présentent un fort intérêt pédagogique mais sont peu spécialisés dans l'écologie réaliste.

## 5. Architecture Technique & Stack

Le projet repose sur une architecture moderne Client-Serveur communiquant en temps réel via WebSocket.

- Moteur de calcul (Backend - Python) : Moteur performant pour modéliser les interactions scientifiques. Il calcule les étapes de l'écosystème en mode discret et génère les logs structurés.
- Moteur de rendu (Frontend - Godot Engine) : Interface utilisateur pour la visualisation interactive en temps réel et multiplateforme.
- Data Science (NumPy, Pandas, SciPy) : Traitement, analyse et export des données générées par la simulation.
- Web (React) : Développement du site vitrine du projet pour la communication et l'acquisition.
- Outils Collaboratifs : Git, GitHub ou GitLab pour le versioning et l'intégration continue.

## 6. Fonctionnalités Principales

- Génération du Monde : Création procédurale ou paramétrée d'une carte avec placement stratégique des ressources (eau, nourriture).
- Entités Autonomes (Agents) : Créatures dotées de sens, de besoins vitaux et de capacités d'action intelligentes (se déplacer, se reposer, manger, boire).
- Contrôle du Temps et Streaming : Interface permettant de précalculer la simulation (compute) puis de la lire comme un flux vidéo interactif avec des contrôles de base (start, pause, resume, stop).
- Rapports de Simulation : Génération de fichiers JSON structurés détaillant avec précision chaque cycle de vie (step) de la simulation.

## 7. Méthodologie de Travail

- Méthode Agile : Organisation itérative avec des réunions de synchronisation hebdomadaires.
- Suivi des tâches : Utilisation d'outils Git (GitHub ou GitLab) pour la gestion de projet.
- Expertise métier : Séparation claire et nette des responsabilités techniques pour une efficacité maximale.
