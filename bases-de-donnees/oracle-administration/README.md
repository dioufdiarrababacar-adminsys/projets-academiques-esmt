# Administration Oracle

> TP d'administration de base de données Oracle : tablespace, profil de mots de passe, utilisateur, privilèges, rôle et export.

**Cadre :** Administration et bases de données (projet 2), Master ISI/SSI, ESMT, 2025-2026. Travail individuel.

## Contenu

- [`rapport.pdf`](rapport.pdf) : le rapport tel que rendu, avec les requêtes SQL pour
  - créer un tablespace de 80 Mo à extension automatique
  - définir un profil de mots de passe (tentatives, verrouillage, durée de vie, réutilisation)
  - créer un utilisateur avec mot de passe expiré, quota et profil
  - accorder et retirer des privilèges objet, créer un rôle et l'attribuer
  - décrire l'export d'un schéma avec l'utilitaire `exp`
- [`corriges.sql`](corriges.sql) : les mêmes réponses, corrigées après relecture.

## Corrections apportées après relecture

- **Privilèges du rôle CAISSE :** la cible doit être `ON HR.EMPLOYEES` et non `ON HR`.
- **Réutilisation des mots de passe :** `PASSWORD_REUSE_MAX` est le nombre de changements de mot de passe exigés avant qu'un ancien puisse être réutilisé, et non un nombre de réutilisations autorisées. Il se combine avec `PASSWORD_REUSE_TIME`.
- **Quota :** `UNLIMITED TABLESPACE` annule le quota de 60 Mo fixé à la création de l'utilisateur et va à l'encontre du moindre privilège. Il est retiré.
- **Export du schéma PROD :** la procédure se connectait en HR. La version corrigée exporte bien PROD, avec Data Pump (`expdp ... schemas=PROD`) ou avec `exp ... owner=PROD`, et sans écrire de mot de passe dans la commande.

`corriges.sql` n'a pas été exécuté sur une instance Oracle : à tester avant usage.
