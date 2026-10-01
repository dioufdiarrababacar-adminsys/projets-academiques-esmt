# Spanza, vidéothèque client/serveur

> Serveur et client TCP en Python pour une vidéothèque en ligne : inscription, connexion, catalogue, téléchargement et téléversement de vidéos, avec deux niveaux d'abonnement. Version corrigée après revue de sécurité.

**Cadre :** Programmation réseau, Master 1 SSI, ESMT. Projet de groupe (voir l'en-tête des fichiers).
**Ma contribution :** _à compléter_

La version rendue se trouve dans l'historique git (premier commit du dépôt). Cette version corrige les failles relevées en relisant ce code.

## Fonctionnement

- Protocole sur TCP : chaque message est un JSON précédé de 4 octets indiquant sa longueur ([`protocole.py`](protocole.py)).
- Serveur multi-clients : un thread par connexion, 50 connexions simultanées au maximum.
- Authentification par nom d'utilisateur et mot de passe, cookie de session lié à la connexion qui l'a reçu.
- Persistance avec peewee et SQLite (abonnés et vidéos).
- Deux groupes d'abonnés :
  - `Spanzo_nada` : limité à 3 Go de téléchargement par fenêtre de 15 minutes
  - `Spanzo_gold` : obtenu en téléversant une vidéo d'au moins 1 Go, sans limite de téléchargement

## Revue de sécurité : ce qui a changé

| Problème de la version rendue | Correction |
|-------------------------------|-----------|
| Trafic en clair (mots de passe, vidéos) | TLS obligatoire côté serveur, certificat vérifié côté client |
| Mots de passe en SHA-256 sans sel | scrypt avec sel aléatoire par utilisateur, comparaison en temps constant, migration automatique des anciens hachages à la connexion |
| Taille de message non bornée : un client annonçait 4 Go et saturait la mémoire | Limite vérifiée avant toute allocation (64 Kio avant authentification, 1 Gio ensuite) |
| Aucune limite sur les tentatives de connexion | Blocage par adresse IP après 5 échecs en 15 minutes |
| Aucun délai d'inactivité, nombre de clients illimité | Délai de 120 s, 50 clients maximum |
| Type de fichier vérifié sur le nom seulement | Extension et signature du contenu (mp4, mov, mkv, webm, avi), base64 validé, taille plafonnée à 700 Mo |
| Client : l'intitulé choisi par un autre abonné servait de nom de fichier, donc `../../x` écrivait hors du dossier | Nom de fichier assaini, préfixé par l'identifiant de la vidéo |
| Extension toujours `.mp4` au téléchargement | Extension fournie par le serveur |
| Vidéos stockées en base64 dans la base (+33 %) | Stockage binaire |
| Quota de téléchargement sujet aux accès concurrents | Verrou autour de la lecture, du contrôle et de la mise à jour |
| Message d'exception renvoyé au client | Message générique, détails dans le journal du serveur |
| Pas de journalisation | Connexions, échecs d'authentification et transferts journalisés |
| Adresse du serveur codée en dur dans le client | Paramètres `--hote`, `--port`, `--ca` |

Les tests ont aussi révélé un bug dans une première version de la correction : `hmac.compare_digest` plantait sur un cookie contenant des caractères non ASCII. Il est corrigé et couvert par un test.

## Lancer le projet

```bash
pip install -r requirements.txt

# Certificat de laboratoire (l'adresse IP doit être celle que le client utilise pour joindre le serveur)
openssl req -x509 -newkey rsa:2048 -nodes -keyout cle.pem -out cert.pem -days 365 \
  -subj "/CN=spanza" -addext "subjectAltName=IP:192.168.1.18,DNS:localhost"

# Serveur (cle.pem ne doit jamais être publiée : elle est exclue par le .gitignore)
SPANZA_CERT=cert.pem SPANZA_KEY=cle.pem python serveur.py

# Client
python client.py --hote 192.168.1.18 --ca cert.pem
```

Sous PowerShell, définir les variables avec `$env:SPANZA_CERT = "cert.pem"`. Pour un essai sans chiffrement, uniquement en laboratoire : `SPANZA_ALLOW_PLAINTEXT=1` côté serveur et `--sans-tls` côté client.

## Tests

```bash
python -m unittest discover -s tests -v
```

22 tests d'intégration contre un vrai serveur TLS sur localhost (nécessite `openssl`) : connexion en clair refusée, message géant refusé, doublon d'inscription, hachage salé, limitation des tentatives, migration de l'ancien hachage, cookie lié à la connexion, contrôle des vidéos (extension, signature, base64), passage en gold, quota, et un parcours complet avec le vrai `client.py` et un titre de vidéo hostile (`../../evil`).

## Fichiers

- [`serveur.py`](serveur.py), [`client.py`](client.py), [`protocole.py`](protocole.py)
- [`tests/test_spanza.py`](tests/test_spanza.py)

## Limites restantes

- La limitation des tentatives est par adresse IP : derrière un NAT partagé, un utilisateur fautif peut bloquer les autres.
- Une vidéo est transférée en un seul message JSON en base64, donc chargée en entier en mémoire des deux côtés (700 Mo au maximum). Un transfert par blocs serait plus sobre.
- Pas de réinitialisation de mot de passe ni d'expiration de session.
- Le certificat auto-signé convient en laboratoire. En production, utiliser un certificat d'une autorité reconnue.
