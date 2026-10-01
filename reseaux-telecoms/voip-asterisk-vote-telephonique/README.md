# Vote téléphonique avec Asterisk

> Centre d'appel IVR qui permet de voter par téléphone (touches DTMF) pour l'un des deux lutteurs d'un combat de lutte traditionnelle, avec affichage des résultats en direct sur une page web.

**Cadre :** Services Réseaux, année scolaire 2024-2025, ESMT. Projet de groupe.
**Ma contribution :** le site web d'affichage des résultats (page PHP, graphique Chart.js).

## Fonctionnement

1. Un softphone (Zoiper, Linphone) enregistré en tant que poste 101 ou 102 appelle le 200.
2. Asterisk joue un message d'accueil, capte la touche pressée et envoie le vote à un script PHP.
3. `enregistrervote.php` insère le vote dans une table MySQL.
4. `resultats.php` affiche les résultats en tableau et en diagramme circulaire (Chart.js).

## Stack

Asterisk 20 (chan_pjsip) sur Ubuntu 24.04, MariaDB/MySQL, PHP, Apache, Chart.js, VirtualBox ou VMware pour les tests.

## Contenu

- [`rapport.pdf`](rapport.pdf) : architecture, configuration, scripts, base de données, captures
- [`src/`](src/) : scripts PHP, schéma SQL, extraits `extensions.conf` et `pjsip.conf`
- [`tests/test-vote.sh`](tests/test-vote.sh) : test du point d'entrée de vote

## Sécurité

- Vote accepté uniquement en POST, depuis la machine locale, avec un jeton partagé avec le dialplan
- Numéro de l'appelant filtré et revalidé, requêtes SQL préparées
- Un vote par numéro, compte SQL limité à l'ajout et à la lecture des votes
- Identifiants hors du dossier web, erreurs jamais affichées

## Tests

```bash
php -S 127.0.0.1:8081 -t src       # avec VOTE_CONFIG pointant vers un config.ini valide
BASE=http://127.0.0.1:8081 TOKEN=<token> ./tests/test-vote.sh
```

Le dialplan (`extensions.conf`) reste à valider sur un serveur Asterisk.

## Limites

Le numéro d'appelant peut être usurpé : « un vote par numéro » limite les abus mais ne prouve pas l'identité du votant. Un vrai scrutin demanderait une authentification des votants.
