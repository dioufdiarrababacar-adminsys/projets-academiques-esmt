# Spanza, vidéothèque client/serveur

> Serveur et client TCP en Python pour une vidéothèque en ligne : inscription, connexion, catalogue, téléchargement et téléversement de vidéos, avec deux niveaux d'abonnement.

**Cadre :** Programmation réseau, Master 1 SSI, ESMT. Projet de groupe.
**Ma contribution :** _à compléter_

## Fonctionnement

- Protocole sur TCP : chaque message est un JSON précédé de 4 octets indiquant sa longueur
- Serveur multi-clients (un thread par connexion), persistance avec peewee et SQLite
- Deux groupes d'abonnés :
  - `Spanzo_nada` : 3 Go de téléchargement maximum par fenêtre de 15 minutes
  - `Spanzo_gold` : obtenu en téléversant une vidéo d'au moins 1 Go, sans limite

## Sécurité

- Connexion chiffrée en TLS, certificat vérifié par le client
- Mots de passe hachés avec scrypt et un sel par utilisateur
- Taille des messages bornée, limitation des tentatives de connexion, délai d'inactivité
- Vidéos contrôlées sur leur extension et leur signature

## Lancer le projet

```bash
pip install -r requirements.txt

# Certificat de laboratoire (l'adresse IP doit être celle que le client utilise pour joindre le serveur)
openssl req -x509 -newkey rsa:2048 -nodes -keyout cle.pem -out cert.pem -days 365 \
  -subj "/CN=spanza" -addext "subjectAltName=IP:192.168.1.18,DNS:localhost"

SPANZA_CERT=cert.pem SPANZA_KEY=cle.pem python serveur.py
python client.py --hote 192.168.1.18 --ca cert.pem
```

Sous PowerShell, définir les variables avec `$env:SPANZA_CERT = "cert.pem"`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Pistes d'amélioration

- Transférer les vidéos par blocs plutôt qu'en un seul message en mémoire
- Réinitialisation de mot de passe et expiration des sessions
