# Administration Oracle

> TP d'administration de base de données Oracle : tablespace, profil de mots de passe, utilisateur, privilèges, rôle et export.

**Cadre :** Administration et bases de données (projet 2), Master ISI/SSI, ESMT, 2025-2026. Travail individuel.

## Contenu

- [`rapport.pdf`](rapport.pdf) : le rapport rendu, avec les requêtes SQL pour
  - créer un tablespace de 80 Mo à extension automatique
  - définir un profil de mots de passe (tentatives, verrouillage, durée de vie, réutilisation)
  - créer un utilisateur avec mot de passe expiré, quota et profil
  - accorder et retirer des privilèges, créer un rôle et l'attribuer
  - exporter un schéma
- [`corriges.sql`](corriges.sql) : les mêmes réponses après relecture, à tester avant usage

## Points corrigés

- Privilèges du rôle `CAISSE` sur `HR.EMPLOYEES` (et non sur `HR`)
- `PASSWORD_REUSE_MAX` : nombre de changements de mot de passe exigés avant réutilisation, à combiner avec `PASSWORD_REUSE_TIME`
- `UNLIMITED TABLESPACE` retiré : il annulait le quota de 60 Mo
- Export du schéma `PROD` (et non `HR`), avec Data Pump
