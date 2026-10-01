-- Projet 2 : réponses corrigées après relecture (Oracle).
-- Non exécuté sur une instance Oracle : syntaxe vérifiée d'après la documentation, à tester avant usage.
-- En architecture multitenant, se placer d'abord dans le PDB : ALTER SESSION SET CONTAINER = orclpdb;

-- 1. Tablespace permanent PROD, fichier de 80 Mo à extension automatique
CREATE TABLESPACE PROD
  DATAFILE 'C:\oracle\oradata\orcl\prod.dbf' SIZE 80M
  AUTOEXTEND ON;

-- 2. Profil param_pwd
CREATE PROFILE param_pwd LIMIT
  FAILED_LOGIN_ATTEMPTS  2    -- compte verrouillé après 2 échecs de connexion
  PASSWORD_LOCK_TIME     3    -- déverrouillage automatique après 3 jours
  PASSWORD_LIFE_TIME     20   -- mot de passe à changer tous les 20 jours
  PASSWORD_REUSE_MAX     3    -- 3 changements de mot de passe exigés avant qu'un ancien soit réutilisable...
  PASSWORD_REUSE_TIME    40;  -- ...et 40 jours écoulés : les deux conditions s'appliquent ensemble

-- 3. Utilisateur PROD
CREATE USER PROD
  IDENTIFIED BY passer123
  PASSWORD EXPIRE                 -- à changer dès la première connexion
  DEFAULT TABLESPACE PROD
  QUOTA 60M ON PROD
  PROFILE param_pwd;

-- 4. Droits de base
GRANT CREATE SESSION TO PROD;     -- se connecter
GRANT CREATE TABLE TO PROD;       -- créer des tables dans son propre schéma
-- Pas de UNLIMITED TABLESPACE : il annulerait le quota de 60 Mo de la question 3 et dépasse le besoin.

-- 5. Lire, ajouter et supprimer dans HR.EMPLOYEES
GRANT SELECT, INSERT, DELETE ON HR.EMPLOYEES TO PROD;

-- 6. Retirer le droit de suppression
REVOKE DELETE ON HR.EMPLOYEES FROM PROD;

-- 7. Rôle CAISSE
CREATE ROLE CAISSE;

-- 8. Privilèges du rôle : la cible est la TABLE HR.EMPLOYEES, pas le schéma HR
GRANT SELECT, INSERT ON HR.EMPLOYEES TO CAISSE;

-- 9. Attribuer le rôle à PROD
GRANT CAISSE TO PROD;

-- 10. Exporter le schéma PROD
-- Une seule fois, en tant qu'administrateur : un répertoire Oracle qui pointe vers le dossier de sauvegarde.
--   CREATE OR REPLACE DIRECTORY SAUVEGARDE AS 'C:\Sauvegarde';
--
-- Puis, dans une invite de commandes Windows. Le mot de passe est demandé par l'outil,
-- il ne s'écrit pas dans la commande (donc ni dans l'historique, ni dans la liste des processus) :
--   expdp system@localhost:1521/orclpdb schemas=PROD directory=SAUVEGARDE dumpfile=prod090626.dmp logfile=prod090626.log
--
-- Ancien utilitaire exp (celui du rapport), avec le bon schéma :
--   exp prod@localhost:1521/orclpdb owner=PROD file=C:\Sauvegarde\prod090626.dmp log=C:\Sauvegarde\prod090626.log
