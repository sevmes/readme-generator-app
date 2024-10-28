# Exemple de documenation générée
Repository utilisé : https://github.com/ddd-by-examples/library

## Partie 1 : Objectif métier du projet "Library"

Ce projet vise à modéliser le système de gestion d'une bibliothèque publique, en se concentrant sur le processus de réservation et d'emprunt de livres.  L'application gère les interactions entre les usagers et les ouvrages disponibles dans les différentes branches de la bibliothèque.

Voici les règles métier principales implémentées :

* **Réservation des livres :** Un usager peut réserver un livre disponible. Un livre ne peut être réservé que par un seul usager à la fois.  Il existe deux types de réservations :
    * **Réservation à durée déterminée :**  Active jusqu'à ce que l'usager emprunte le livre ou que la réservation expire. Une réservation expire après un nombre de jours défini lors de la réservation.  Ce type de réservation est accessible à tous les usagers.
    * **Réservation à durée indéterminée :** Active jusqu'à ce que l'usager emprunte le livre. Seul un usager de type "chercheur" peut effectuer ce type de réservation.

* **Types d'usagers :**  Deux types d'usagers sont gérés :
    * **Usager régulier :** Limité à cinq réservations simultanées.
    * **Usager chercheur :**  Autorisé à un nombre illimité de réservations et peut réserver des livres à accès restreint.

* **Types de livres :**  Les livres sont classés en deux catégories :
    * **Livres en circulation :** Accessibles à tous les usagers.
    * **Livres à accès restreint :**  Réservables uniquement par les chercheurs.

* **Emprunts :** Un livre peut être emprunté pour une durée maximale de 60 jours.  Le système vérifie quotidiennement les emprunts en retard.

* **Retards :** Un usager ayant plus de deux emprunts en retard dans une branche donnée se verra refuser toute nouvelle réservation dans cette branche.

* **Profil usager :**  Chaque usager dispose d'un profil lui permettant de consulter ses réservations et emprunts en cours, y compris ceux en retard.  Il peut également effectuer une réservation ou annuler une réservation existante via son profil.

* **Catalogue :** La bibliothèque possède un catalogue contenant la liste des livres disponibles avec leurs instances spécifiques. Une instance de livre ne peut être ajoutée que si un livre avec le même ISBN est déjà présent dans le catalogue.  Chaque livre doit avoir un titre et un prix. Lors de l'ajout d'une instance, son type (en circulation ou à accès restreint) est défini.


## Partie 2 : Fonctionnement interne du projet "Library"

Le projet est structuré en deux contextes bornés principaux :  "catalogue" et "lending" (emprunt).  Cette séparation vise à découpler les différentes parties du système et à faciliter l'évolution et la maintenance.

* **Contexte "catalogue" :**  Implémenté comme un simple CRUD (Create, Read, Update, Delete) sans logique métier complexe.  Il gère l'ajout, la modification et la suppression des livres et de leurs instances dans le catalogue.  Utilise Spring Data JDBC pour la persistance.

* **Contexte "lending" :**  Contient la logique métier principale du système, notamment la gestion des réservations, des emprunts et des retards.  Ce contexte utilise l'architecture hexagonale pour séparer la logique métier de l'infrastructure.

**Aspects techniques clés :**

* **Architecture hexagonale :**  Permet de découpler le modèle de domaine de l'infrastructure et des frameworks.  Facilite les tests unitaires et l'évolution du système.

* **Programmation fonctionnelle :**  Le code utilise des concepts de programmation fonctionnelle tels que les objets immuables, les fonctions pures et les monades (Vavr) pour améliorer la clarté et la testabilité du code.

* **Spring Framework :**  Utilisé pour l'infrastructure, notamment pour la gestion des événements, la persistance (Spring Data JDBC) et l'exposition des API REST.  Chaque contexte borné possède son propre contexte d'application Spring pour minimiser le couplage.

* **Tests :**  Le projet inclut des tests unitaires et d'intégration écrits en Groovy (Spock) suivant une approche BDD (Behavior-Driven Development).  Un DSL (Domain Specific Language) est utilisé pour rendre les tests plus lisibles et expressifs.

* **Gestion des événements :**  Le système utilise un bus d'événements pour la communication entre les agrégats.  Deux implémentations du bus d'événements sont fournies : une synchrone (immédiate) et une asynchrone (éventuelle) pour illustrer les différentes options de cohérence.

* **Persistance :**  Le projet utilise Spring Data JDBC pour la persistance des données.  Une alternative utilisant JdbcTemplate et des requêtes SQL est également proposée.

* **Monitoring :**  Intégration avec Prometheus et Grafana pour la collecte et la visualisation des métriques.


Ce découpage et ces choix techniques visent à créer une application robuste, maintenable et évolutive, capable de gérer la complexité du domaine métier de la bibliothèque.
