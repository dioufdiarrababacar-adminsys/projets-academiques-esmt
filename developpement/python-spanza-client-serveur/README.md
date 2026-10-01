# Spanza, vidéothèque client/serveur

> Serveur et client TCP en Python pour une vidéothèque en ligne : inscription, connexion, catalogue, téléchargement et téléversement de vidéos, avec deux niveaux d'abonnement.

**Cadre :** Programmation réseau, Master 1 SSI, ESMT. Projet de groupe (voir l'en-tête des fichiers).
**Ma contribution :** _à compléter_

## Fonctionnement

- Protocole maison sur TCP : chaque message est un JSON précédé de 4 octets indiquant sa longueur, ce qui permet d'échanger des fichiers volumineux sans troncature.
- Serveur multi-clients : un thread par connexion.
- Authentification par nom d'utilisateur et mot de passe. Le serveur délivre un cookie de session (UUID) à présenter à chaque commande.
- Persistance avec peewee et SQLite (abonnés et vidéos).
- Deux groupes d'abonnés :
  - `Spanzo_nada` : limité à 3 Go de téléchargement par fenêtre de 15 minutes
  - `Spanzo_gold` : obtenu en téléversant une vidéo d'au moins 1 Go, sans limite de téléchargement
- Seules les extensions vidéo (mp4, mkv, avi, mov, webm) sont acceptées au téléversement.

## Lancer le projet

```bash
pip install peewee
python serveur.py        # écoute sur le port 5000, crée spanza.db au premier lancement
python client.py         # adapter HOTE (adresse IP du serveur) au début du fichier
```

## Fichiers

- [`serveur.py`](serveur.py)
- [`client.py`](client.py)

## Limites connues

- Aucun chiffrement : mots de passe et vidéos circulent en clair sur le réseau (pas de TLS).
- Les mots de passe sont hachés en SHA-256 sans sel.
- La taille d'un message n'est pas bornée côté serveur : un client peut annoncer une longueur énorme et saturer la mémoire.
- Le type de fichier est vérifié sur l'extension du nom, pas sur le contenu.
- Les vidéos sont stockées en base64 dans la base de données, ce qui ajoute environ un tiers de volume et ne passe pas à l'échelle.
- Pas de limitation des tentatives de connexion.
