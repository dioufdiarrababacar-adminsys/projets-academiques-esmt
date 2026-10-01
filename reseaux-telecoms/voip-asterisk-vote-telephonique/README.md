# Vote téléphonique avec Asterisk

> Centre d'appel IVR qui permet de voter par téléphone (touches DTMF) pour l'un des deux lutteurs d'un combat de lutte traditionnelle, avec affichage des résultats en direct sur une page web. Sources reconstituées et corrigées après revue de sécurité.

**Cadre :** Services Réseaux, année scolaire 2024-2025, ESMT. Projet de groupe (voir la page de garde du rapport).
**Ma contribution :** _à compléter_

## Ce que fait le système

1. Un softphone (Zoiper, Linphone) enregistré en tant que poste 101 ou 102 appelle le 200.
2. Asterisk joue un message d'accueil, capte la touche pressée et envoie le vote à un script PHP avec `curl`.
3. `enregistrervote.php` insère le vote dans une table MySQL.
4. `resultats.php` agrège les votes et les affiche en tableau et en diagramme circulaire (Chart.js).

## Stack

Asterisk 20 (chan_pjsip) sur Ubuntu 24.04, MariaDB/MySQL, PHP, Apache, Chart.js, VirtualBox ou VMware pour les tests.

## Contenu

- [`rapport.pdf`](rapport.pdf) : architecture, configuration, scripts, base de données, captures. C'est le document rendu, il décrit la version d'origine.
- [`src/`](src/) : les sources, reconstituées à partir des captures du rapport puis corrigées.
  - [`enregistrervote.php`](src/enregistrervote.php), [`resultats.php`](src/resultats.php)
  - [`schema.sql`](src/schema.sql), [`config.example.ini`](src/config.example.ini)
  - [`extensions.conf`](src/extensions.conf), [`pjsip.conf`](src/pjsip.conf) (extraits, sans mot de passe réel)
- [`tests/test-vote.sh`](tests/test-vote.sh) : test de fumée du point d'entrée de vote.

Le rapport décrit les touches de façon contraire au dialplan de la capture (le texte dit 1 pour Balla Gaye, la configuration affichée envoie la touche 1 vers Modou Lô). Les sources ici suivent la configuration.

## Revue de sécurité : ce qui a changé

| Problème de la version rendue | Correction |
|-------------------------------|-----------|
| `enregistrervote.php` acceptait un simple GET public : n'importe qui pouvait voter sans appeler | POST uniquement, depuis localhost uniquement, avec un jeton secret partagé avec le dialplan |
| Le paramètre `vote` (texte libre) était recopié en base | La touche est validée (1 ou 2) et traduite en nom de candidat côté serveur |
| Le numéro de l'appelant (`CALLERID`), contrôlé par l'appelant SIP, était inséré tel quel dans la commande shell `curl` : injection de commande possible | `${FILTER(0-9,...)}` ne garde que les chiffres, et le script PHP revalide le numéro |
| Échappement manuel (`real_escape_string`) | Requêtes préparées PDO |
| Mot de passe de la base écrit dans le script web, `display_errors` actif | Identifiants dans un fichier hors du dossier web, erreurs écrites dans le journal et jamais affichées |
| Un même numéro pouvait voter autant de fois qu'il voulait | Contrainte `UNIQUE` sur le numéro : un vote par numéro |
| Même compte MySQL que le reste de la base | Compte `votes_app` limité à `INSERT` et `SELECT` sur la table `votes` |
| Mots de passe SIP en `123456` | Valeurs à générer aléatoirement (`CHANGER_MOI`) |
| Colonne `vote` en doublon de `candidat`, schéma du rapport différent de celui des captures | Schéma unique et documenté, avec requêtes de migration |
| `resultats.php` : division par zéro possible, sortie non échappée, Chart.js non figé | Cas sans vote géré, sortie échappée, version figée et vérifiée par SRI |

## Tests

Joués sur MariaDB 10.4 et PHP 8.0 (serveur intégré `php -S`) :

```bash
php -S 127.0.0.1:8081 -t src       # avec VOTE_CONFIG pointant vers un config.ini valide
BASE=http://127.0.0.1:8081 TOKEN=<token> ./tests/test-vote.sh
```

10 contrôles : GET refusé, POST sans jeton ou avec mauvais jeton refusés, vote valide, second vote du même numéro refusé (409), touche inconnue refusée, injection SQL et injection shell dans le numéro refusées, page de résultats accessible. Vérifiés aussi à la main : accès depuis une autre adresse que localhost refusé, compte `votes_app` incapable de `DELETE` ou `DROP`, page de résultats sans vote, et base arrêtée (message générique, aucun détail technique).

**Non testé :** le dialplan (`extensions.conf`) et `pjsip.conf`, faute d'Asterisk sur la machine de test. La syntaxe suit la documentation (`Gosub`, `FILTER`, `System`, `SYSTEMSTATUS`) mais doit être essayée sur le serveur. Les messages `vote_modou_lo` et `vote_balla_gaye` sont ceux du projet d'origine.

## Limites restantes

- Le numéro d'appelant (`CALLERID`) peut être usurpé par un poste SIP : « un vote par numéro » limite les abus mais ne prouve pas l'identité du votant. Un vrai scrutin demanderait une authentification des votants, comme l'indiquent les perspectives du rapport.
- Ni anti-brute-force sur les postes SIP (fail2ban), ni TLS/SRTP : à ajouter avant toute exposition sur Internet.
