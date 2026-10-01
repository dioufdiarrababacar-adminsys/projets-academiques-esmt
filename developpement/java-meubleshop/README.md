# MeubleShop

> Application de bureau Java de gestion de vente de meubles : catalogue, clients, caisse, historique des ventes et gestion des utilisateurs.

**Cadre :** Programmation orientée objet (Java), Master 1 SSI, ESMT, année académique 2025-2026. Projet de groupe (voir la page de garde du rapport).
**Ma contribution :** _à compléter_

## Fonctionnalités

- Authentification avec deux profils, administrateur et vendeur
- Tableau de bord : indicateurs calculés par requêtes SQL d'agrégation, alertes de stock, meilleures ventes
- CRUD des meubles et des clients, avec recherche et filtres
- Caisse : panier, contrôle du stock, enregistrement de la facture
- Historique des ventes filtré par période, avec détail des factures
- Gestion des comptes réservée à l'administrateur

## Points techniques

- Architecture en couches avec classes DAO
- Connexion JDBC centralisée (patron Singleton), paramètres lus dans `config.properties`
- Requêtes préparées (`PreparedStatement`) contre l'injection SQL
- Enregistrement d'une vente dans une transaction JDBC (commit, rollback en cas d'échec)
- Interface Swing, livraison sous forme de JAR exécutable

## Contenu

- [`rapport.pdf`](rapport.pdf) : présentation de l'application, extraits de code commentés, déploiement.
- [`meuble.sql`](meuble.sql) : création de la base `meuble` (tables, jeu de données de démonstration, vue `vue_ventes`).
- [`config.properties.example`](config.properties.example) : modèle du fichier de configuration de la connexion MySQL.

Le code source complet n'est pas dans ce dépôt, seuls des extraits figurent dans le rapport.

## Installation

1. Démarrer MySQL ou MariaDB (XAMPP, WampServer).
2. Importer `meuble.sql` (phpMyAdmin, ou `mysql < meuble.sql`).
3. Copier `config.properties.example` en `config.properties` à côté du JAR et renseigner l'utilisateur et le mot de passe MySQL.
4. Placer le pilote MySQL Connector/J dans `lib/`, puis lancer `java -jar Meuble.jar`.

## Limites connues (non corrigées : le code source n'est pas disponible)

Seuls le JAR compilé (non publié dans ce dépôt) et le rapport sont disponibles, donc rien n'a pu être corrigé dans le code. Ce qu'il faudrait changer dans les sources :

- Les mots de passe sont hachés en SHA-256 sans sel. Pour un usage réel, il faudrait un algorithme dédié (bcrypt ou Argon2).
- L'URL JDBC est écrite en dur avec `useSSL=false` et `allowPublicKeyRetrieval=true` : la liaison avec la base n'est pas chiffrée. Acceptable en local, pas sur un réseau.
- Les comptes de démonstration (admin, vendeur, caisse) sont documentés dans le rapport et ne doivent pas être conservés en production.
