-- =====================================================================
-- Projet 12 : Application de gestion de vente de meubles de maison
-- Groupe 12 - Ecole Superieure Multinationale des Telecommunications
-- Base de donnees : meuble
-- SGBD : MySQL / MariaDB
-- Export a importer dans phpMyAdmin (Importer > choisir meuble.sql)
-- =====================================================================

DROP DATABASE IF EXISTS `meuble`;
CREATE DATABASE `meuble` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `meuble`;

-- ---------------------------------------------------------------------
-- Table : utilisateur (authentification)
-- Les mots de passe sont stockes sous forme d'empreinte SHA-256.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `utilisateur`;
CREATE TABLE `utilisateur` (
  `id`            INT(11)      NOT NULL AUTO_INCREMENT,
  `login`         VARCHAR(50)  NOT NULL,
  `mot_de_passe`  VARCHAR(255) NOT NULL,
  `nom_complet`   VARCHAR(100) NOT NULL,
  `role`          VARCHAR(20)  NOT NULL DEFAULT 'VENDEUR',
  `actif`         TINYINT(1)   NOT NULL DEFAULT 1,
  `date_creation` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_login` (`login`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Mots de passe en clair (pour la demonstration) :
--   admin   -> admin123
--   vendeur -> vendeur123
--   caisse  -> caisse123
INSERT INTO `utilisateur` (`id`, `login`, `mot_de_passe`, `nom_complet`, `role`, `actif`) VALUES
(1, 'admin',   '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrateur Systeme', 'ADMIN',   1),
(2, 'vendeur', '569dba69daa0e283c3a5498adc2011f7830fab26074ca7eebc7cc47c5e4b9493', 'Awa Ndiaye',             'VENDEUR', 1),
(3, 'caisse',  '1906ae45642ea4a63dd6cf94df948d65c75e0c0a845b5d3f0cac6a9c9e6f1dd2', 'Moussa Diop',            'VENDEUR', 1);

-- ---------------------------------------------------------------------
-- Table : categorie
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `categorie`;
CREATE TABLE `categorie` (
  `id`      INT(11)      NOT NULL AUTO_INCREMENT,
  `libelle` VARCHAR(60)  NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_libelle` (`libelle`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `categorie` (`id`, `libelle`) VALUES
(1, 'Chambre'),
(2, 'Salon'),
(3, 'Salle a manger'),
(4, 'Cuisine'),
(5, 'Bureau'),
(6, 'Rangement');

-- ---------------------------------------------------------------------
-- Table : meuble (catalogue des articles)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `meuble`;
CREATE TABLE `meuble` (
  `id`             INT(11)        NOT NULL AUTO_INCREMENT,
  `reference`      VARCHAR(30)    NOT NULL,
  `designation`    VARCHAR(120)   NOT NULL,
  `id_categorie`   INT(11)        NOT NULL,
  `matiere`        VARCHAR(60)             DEFAULT NULL,
  `couleur`        VARCHAR(40)             DEFAULT NULL,
  `prix_unitaire`  DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
  `quantite_stock` INT(11)        NOT NULL DEFAULT 0,
  `seuil_alerte`   INT(11)        NOT NULL DEFAULT 2,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_reference` (`reference`),
  KEY `fk_meuble_categorie` (`id_categorie`),
  CONSTRAINT `fk_meuble_categorie` FOREIGN KEY (`id_categorie`) REFERENCES `categorie` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `meuble` (`id`, `reference`, `designation`, `id_categorie`, `matiere`, `couleur`, `prix_unitaire`, `quantite_stock`, `seuil_alerte`) VALUES
(1,  'LIT-160', 'Lit double 160x200',            1, 'Bois massif',  'Marron',     185000.00, 12, 3),
(2,  'LIT-090', 'Lit simple 90x190',             1, 'Bois massif',  'Blanc',      110000.00, 18, 4),
(3,  'ARM-3P',  'Armoire 3 portes avec miroir',  1, 'MDF',          'Chene clair',245000.00,  6, 3),
(4,  'ARM-2P',  'Armoire 2 portes',              1, 'MDF',          'Blanc',      160000.00,  2, 3),
(5,  'CHV-01',  'Chevet 2 tiroirs',              1, 'Bois massif',  'Marron',      35000.00, 25, 5),
(6,  'CAN-3PL', 'Canape 3 places en tissu',      2, 'Tissu',        'Gris',       320000.00,  5, 2),
(7,  'CAN-ANG', 'Canape d angle convertible',    2, 'Simili cuir',  'Noir',       450000.00,  3, 2),
(8,  'TBS-01',  'Table basse rectangulaire',     2, 'Verre / metal','Transparent', 75000.00, 10, 3),
(9,  'MTV-01',  'Meuble TV 150 cm',              2, 'MDF',          'Noir',        95000.00,  8, 3),
(10, 'TAB-6P',  'Table a manger 6 places',       3, 'Bois massif',  'Marron',     230000.00,  4, 2),
(11, 'CHA-STD', 'Chaise rembourree',             3, 'Bois / tissu', 'Beige',       22000.00, 40, 8),
(12, 'BUF-01',  'Buffet de salle a manger',      3, 'MDF',          'Chene fonce',185000.00,  3, 2),
(13, 'CUI-HAU', 'Meuble haut de cuisine',        4, 'MDF',          'Blanc',       68000.00,  7, 3),
(14, 'CUI-BAS', 'Meuble bas de cuisine 3 tiroirs',4,'MDF',          'Blanc',       89000.00,  9, 3),
(15, 'BUR-01',  'Bureau informatique',           5, 'MDF / metal',  'Noir',        85000.00, 11, 3),
(16, 'BUR-CHS', 'Chaise de bureau ergonomique',  5, 'Maille',       'Noir',        65000.00,  6, 3),
(17, 'BIB-05',  'Bibliotheque 5 etageres',       5, 'MDF',          'Chene clair', 78000.00,  1, 3),
(18, 'COM-04',  'Commode 4 tiroirs',             6, 'Bois massif',  'Marron',     125000.00,  5, 2),
(19, 'ETG-01',  'Etagere murale',                6, 'Bois',         'Naturel',     18000.00, 30, 6),
(20, 'CHR-01',  'Chariot de rangement 3 niveaux',6, 'Metal',        'Blanc',       27000.00,  2, 4);

-- ---------------------------------------------------------------------
-- Table : client
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `client`;
CREATE TABLE `client` (
  `id`         INT(11)      NOT NULL AUTO_INCREMENT,
  `nom`        VARCHAR(60)  NOT NULL,
  `prenom`     VARCHAR(60)           DEFAULT NULL,
  `telephone`  VARCHAR(30)           DEFAULT NULL,
  `email`      VARCHAR(100)          DEFAULT NULL,
  `adresse`    VARCHAR(150)          DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `client` (`id`, `nom`, `prenom`, `telephone`, `email`, `adresse`) VALUES
(1, 'Diallo',  'Fatou',    '77 123 45 67', 'fatou.diallo@mail.com',  'Sacre Coeur 3, Dakar'),
(2, 'Sarr',    'Ibrahima', '76 987 65 43', 'i.sarr@mail.com',        'Parcelles Assainies, Dakar'),
(3, 'Ba',      'Aminata',  '78 456 78 90', 'aminata.ba@mail.com',    'Mermoz, Dakar'),
(4, 'Faye',    'Ousmane',  '70 321 65 09', 'o.faye@mail.com',        'Thies'),
(5, 'Camara',  'Mariama',  '77 555 22 11', 'm.camara@mail.com',      'Guediawaye'),
(6, 'Sow',     'Cheikh',   '76 111 33 22', 'cheikh.sow@mail.com',    'Rufisque');

-- ---------------------------------------------------------------------
-- Table : vente (en-tete de facture)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `vente`;
CREATE TABLE `vente` (
  `id`             INT(11)       NOT NULL AUTO_INCREMENT,
  `numero`         VARCHAR(30)   NOT NULL,
  `date_vente`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `id_client`      INT(11)       NOT NULL,
  `id_utilisateur` INT(11)       NOT NULL,
  `montant_total`  DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  `mode_paiement`  VARCHAR(30)            DEFAULT 'Especes',
  PRIMARY KEY (`id`),
  KEY `fk_vente_client` (`id_client`),
  KEY `fk_vente_utilisateur` (`id_utilisateur`),
  CONSTRAINT `fk_vente_client` FOREIGN KEY (`id_client`) REFERENCES `client` (`id`),
  CONSTRAINT `fk_vente_utilisateur` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `vente` (`id`, `numero`, `date_vente`, `id_client`, `id_utilisateur`, `montant_total`, `mode_paiement`) VALUES
(1, 'FCT-2026-0001', '2026-07-14 10:25:00', 1, 2, 430000.00, 'Especes'),
(2, 'FCT-2026-0002', '2026-07-21 16:40:00', 3, 2, 320000.00, 'Mobile Money'),
(3, 'FCT-2026-0003', '2026-08-03 11:05:00', 2, 3, 362000.00, 'Carte bancaire'),
(4, 'FCT-2026-0004', '2026-08-08 09:30:00', 5, 2, 150000.00, 'Mobile Money'),
(5, 'FCT-2026-0005', '2026-08-10 15:15:00', 4, 3, 320000.00, 'Especes');

-- ---------------------------------------------------------------------
-- Table : ligne_vente (detail de la facture)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `ligne_vente`;
CREATE TABLE `ligne_vente` (
  `id`            INT(11)       NOT NULL AUTO_INCREMENT,
  `id_vente`      INT(11)       NOT NULL,
  `id_meuble`     INT(11)       NOT NULL,
  `quantite`      INT(11)       NOT NULL DEFAULT 1,
  `prix_unitaire` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`id`),
  KEY `fk_ligne_vente` (`id_vente`),
  KEY `fk_ligne_meuble` (`id_meuble`),
  CONSTRAINT `fk_ligne_vente`  FOREIGN KEY (`id_vente`)  REFERENCES `vente` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ligne_meuble` FOREIGN KEY (`id_meuble`) REFERENCES `meuble` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ligne_vente` (`id`, `id_vente`, `id_meuble`, `quantite`, `prix_unitaire`) VALUES
(1,  1, 1,  1, 185000.00),
(2,  1, 3,  1, 245000.00),
(3,  2, 6,  1, 320000.00),
(4,  3, 10, 1, 230000.00),
(5,  3, 11, 6,  22000.00),
(6,  4, 2,  1, 110000.00),
(7,  4, 19, 1,  18000.00),
(8,  4, 11, 1,  22000.00),
(9,  5, 15, 1,  85000.00),
(10, 5, 16, 1,  65000.00),
(11, 5, 9,  1,  95000.00),
(12, 5, 8,  1,  75000.00);

-- ---------------------------------------------------------------------
-- Vue : recapitulatif des ventes (utile pour les requetes de rapport)
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS `vue_ventes`;
CREATE VIEW `vue_ventes` AS
SELECT v.`id`,
       v.`numero`,
       v.`date_vente`,
       CONCAT(c.`prenom`, ' ', c.`nom`) AS `client`,
       u.`nom_complet`                  AS `vendeur`,
       v.`mode_paiement`,
       v.`montant_total`
FROM `vente` v
JOIN `client` c      ON c.`id` = v.`id_client`
JOIN `utilisateur` u ON u.`id` = v.`id_utilisateur`;

-- ---------------------------------------------------------------------
-- Requetes de verification
-- ---------------------------------------------------------------------
-- SELECT * FROM vue_ventes ORDER BY date_vente DESC;
-- SELECT designation, quantite_stock FROM meuble WHERE quantite_stock <= seuil_alerte;
-- SELECT SUM(montant_total) AS chiffre_affaires FROM vente;
