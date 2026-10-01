# Vote téléphonique avec Asterisk

> Centre d'appel IVR qui permet de voter par téléphone (touches DTMF) pour l'un des deux lutteurs d'un combat de lutte traditionnelle, avec affichage des résultats en direct sur une page web.

**Cadre :** Services Réseaux, année scolaire 2024-2025, ESMT. Projet de groupe (voir la page de garde du rapport).
**Ma contribution :** _à compléter_

## Ce que fait le système

1. Un softphone (Zoiper, Linphone) enregistré en tant que poste 101 ou 102 appelle le 200.
2. Asterisk joue un message d'accueil, capte la touche pressée et appelle un script PHP avec `curl`.
3. `enregistrervote.php` insère le vote dans une table MySQL.
4. `resultats.php` agrège les votes et les affiche en tableau et en diagramme circulaire (Chart.js).

## Stack

Asterisk 20 (chan_pjsip) sur Ubuntu 24.04, MariaDB/MySQL, PHP (MySQLi), Apache, Chart.js, VirtualBox ou VMware pour les tests.

## Contenu

- [`rapport.pdf`](rapport.pdf) : architecture, configuration `pjsip.conf` et `extensions.conf`, scripts PHP, base de données, captures.

Le code source (scripts PHP, fichiers de configuration) n'est pas dans ce dépôt. Il apparaît sous forme de captures dans le rapport.

## Limites connues

- L'endpoint `enregistrervote.php` accepte une simple requête GET et n'authentifie pas l'appelant : il est possible de voter sans passer d'appel.
- Les mots de passe des postes SIP et de la base sont des valeurs de démonstration, et `display_errors` est activé dans le script. Ce n'est acceptable qu'en laboratoire.
- Le rapport évoque l'authentification des votants comme piste d'amélioration, pour éviter les votes multiples.
