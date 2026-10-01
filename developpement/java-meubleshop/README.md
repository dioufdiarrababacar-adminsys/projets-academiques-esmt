# MeubleShop

> Application de bureau Java de gestion de vente de meubles : catalogue, clients, caisse, historique des ventes et gestion des utilisateurs.

**Cadre :** Programmation orientée objet (Java), Master 1 SSI, ESMT, année académique 2025-2026. Projet de groupe.
**Ma contribution :** _à compléter_

## Fonctionnalités

- Authentification avec deux profils, administrateur et vendeur
- Tableau de bord : indicateurs, alertes de stock, meilleures ventes
- CRUD des meubles et des clients, avec recherche et filtres
- Caisse : panier, contrôle du stock, enregistrement de la facture
- Historique des ventes filtré par période, avec détail des factures
- Gestion des comptes réservée à l'administrateur

## Points techniques

- Architecture en couches avec classes DAO
- Connexion JDBC centralisée (patron Singleton), paramètres lus dans `config.properties`
- Requêtes préparées contre l'injection SQL
- Enregistrement d'une vente dans une transaction JDBC (commit, rollback en cas d'échec)
- Interface Swing, livraison sous forme de JAR exécutable

## Contenu

- [`rapport.pdf`](rapport.pdf) : présentation, extraits de code commentés, déploiement
- [`meuble.sql`](meuble.sql) : création de la base `meuble` avec un jeu de données de démonstration
- [`config.properties.example`](config.properties.example) : modèle de la configuration MySQL

## Installation

1. Démarrer MySQL ou MariaDB (XAMPP, WampServer).
2. Importer `meuble.sql`.
3. Copier `config.properties.example` en `config.properties` à côté du JAR et renseigner l'utilisateur et le mot de passe MySQL.
4. Placer le pilote MySQL Connector/J dans `lib/`, puis lancer `java -jar Meuble.jar`.

## Pistes d'amélioration

- Hacher les mots de passe avec bcrypt ou Argon2 plutôt qu'avec SHA-256 sans sel
- Chiffrer la liaison avec la base (l'URL JDBC désactive SSL)
