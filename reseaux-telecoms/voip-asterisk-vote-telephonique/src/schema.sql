-- Base du vote téléphonique (MySQL / MariaDB).
-- À importer avec un compte administrateur : mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS asteriskcdrdb DEFAULT CHARACTER SET utf8mb4;
USE asteriskcdrdb;

CREATE TABLE IF NOT EXISTS votes (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  votant    VARCHAR(20) NOT NULL,                       -- numéro de l'appelant (chiffres uniquement)
  candidat  VARCHAR(50) NOT NULL,
  date_vote TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_votant (votant),                        -- un seul vote par numéro
  KEY idx_candidat (candidat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Compte dédié au site web : il ne peut qu'ajouter et lire des votes
-- (la version rendue utilisait le même compte que le reste de la base).
CREATE USER IF NOT EXISTS 'votes_app'@'localhost' IDENTIFIED BY 'CHANGER_MOI';
GRANT INSERT, SELECT ON asteriskcdrdb.votes TO 'votes_app'@'localhost';

-- Migration depuis l'ancienne table (colonnes id, votant, vote, date_vote, candidat) :
--   ALTER TABLE votes DROP COLUMN vote;                -- doublon de la colonne candidat
--   DELETE v1 FROM votes v1 JOIN votes v2             -- garder le premier vote de chaque numéro
--     ON v1.votant = v2.votant AND v1.id > v2.id;
--   ALTER TABLE votes ADD UNIQUE KEY uk_votant (votant);
