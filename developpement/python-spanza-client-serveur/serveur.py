#Diarra Babacar DIOUF
#Selbe DIOUF
#Jean Pierre Ngor SENE
#Yaye Aby SOW
#Mouhameth WADE


from peewee import *
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from json import loads, dumps
import uuid
import threading
import base64
import os
import hashlib
import time

# ── Base de données ──────────────────────────
db = SqliteDatabase("spanza.db")


class Abonne(Model):
    nom                   = CharField()
    prenom                = CharField(null=True)
    username              = CharField(unique=True)
    password              = CharField(max_length=64, null=False)   # hash SHA-256
    groupe                = CharField(default="Spanzo_nada")
    total_televerse_mo    = FloatField(default=0.0)
    nb_videos_1go         = IntegerField(default=0)
    # Suivi téléchargements pour la limite Spanzo_nada (3 Go / 15 min)
    telechargement_mo_fenetre  = FloatField(default=0.0)   # Mo téléchargés dans la fenêtre courante
    telechargement_debut       = FloatField(default=0.0)   # timestamp de début de fenêtre

    class Meta:
        database = db


class Video(Model):
    intitule    = CharField()
    description = CharField()
    taille_mo   = FloatField()
    contenu_b64 = TextField()

    class Meta:
        database = db


db.connect()
db.create_tables([Abonne, Video], safe=True)

# ── Cookies (sessions) ────────────────────────
cookies      = {}          # {cookie_string: username}
cookies_lock = threading.Lock()   # accès thread-safe

# ── Constantes ───────────────────────────────
SEUIL_GOLD_MO    = 1024        # 1 Go
LIMITE_NADA_MO   = 3 * 1024    # 3 Go
FENETRE_SECONDES = 15 * 60     # 15 minutes
EXTENSIONS_OK    = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

HOST = ""
PORT = 5000


# ── Fonctions utilitaires ────────────────────

def hacher_password(password: str) -> str:
    """Retourne le hash SHA-256 du mot de passe."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def est_video(nom_fichier: str) -> bool:
    _, ext = os.path.splitext(nom_fichier.lower())
    return ext in EXTENSIONS_OK


def get_liste_videos():
    return [
        {
            "id": v.id,
            "intitule": v.intitule,
            "description": v.description,
            "taille_mo": v.taille_mo,
        }
        for v in Video.select()
    ]


# ── Protocole de communication (longueur préfixée) ──────────────────────────
# Chaque message est précédé de 4 octets (big-endian) indiquant sa longueur.
# Cela permet de transférer des fichiers volumineux sans troncature.

def envoyer(sock, dico: dict):
    """Sérialise dico en JSON et l'envoie avec un préfixe de longueur 4 octets."""
    data = dumps(dico, ensure_ascii=False).encode("utf-8")
    longueur = len(data).to_bytes(4, "big")
    sock.sendall(longueur + data)


def recevoir(sock) -> dict:
    """Reçoit un message préfixé par sa longueur et le désérialise."""
    # Lire exactement 4 octets pour la longueur
    entete = b""
    while len(entete) < 4:
        chunk = sock.recv(4 - len(entete))
        if not chunk:
            raise ConnectionError("Connexion fermée par le client.")
        entete += chunk

    longueur = int.from_bytes(entete, "big")

    # Lire exactement longueur octets
    data = b""
    while len(data) < longueur:
        chunk = sock.recv(min(65536, longueur - len(data)))
        if not chunk:
            raise ConnectionError("Connexion fermée pendant la réception.")
        data += chunk

    return loads(data.decode("utf-8"))


def envoyer_texte(sock, texte: str):
    """Envoie un message texte simple (préfixé) pour la phase inscription/connexion."""
    envoyer(sock, {"__texte__": texte})


# ── Gestion d'un client ──────────────────────

def traiter_client(client_socket, client_addr):
    print(f"[+] Connexion de {client_addr}")
    cookie_session = None   # pour le nettoyage en cas d'erreur

    try:
        # ── ÉTAPE 1 : Choix inscription ou connexion ──────────────────────
        envoyer(sock=client_socket, dico={
            "__texte__": "Bienvenue sur Spanza ! Tapez 'inscription' ou 'connexion'."
        })
        choix = recevoir(client_socket).get("choix", "").strip().lower()

        if choix == "inscription":
            # ── INSCRIPTION ──────────────────────────────────────────────
            envoyer_texte(client_socket, "Envoie tes données pour t'inscrire.")
            data = recevoir(client_socket)

            try:
                Abonne.create(
                    nom=data["nom"],
                    prenom=data.get("prenom", ""),
                    username=data["username"],
                    password=hacher_password(data["password"]),
                )
                envoyer_texte(client_socket, "Inscription réussie ! Connecte-toi maintenant.")
            except IntegrityError:
                envoyer(client_socket, {
                    "__texte__": "ERREUR : ce username est déjà pris."
                })
                return

        elif choix == "connexion":
            pass   # on passe directement à l'authentification ci-dessous

        else:
            envoyer(client_socket, {"__texte__": "Choix invalide. Au revoir."})
            return

        # ── ÉTAPE 2 : AUTHENTIFICATION ───────────────────────────────────
        envoyer_texte(client_socket, "Entre ton username et ton password.")
        creds = recevoir(client_socket)

        try:
            abonne_auth = Abonne.get(Abonne.username == creds["username"])
        except Abonne.DoesNotExist:
            envoyer(client_socket, {"cookie": "Bad password"})
            return

        if abonne_auth.password != hacher_password(creds["password"]):
            envoyer(client_socket, {"cookie": "Bad password"})
            return

        # Génère et enregistre le cookie de session
        cookie_session = str(uuid.uuid4())
        with cookies_lock:
            cookies[cookie_session] = abonne_auth.username

        envoyer(client_socket, {"cookie": cookie_session})
        print(f"    [{client_addr}] Connecté en tant que '{abonne_auth.username}'")

        # ── ÉTAPE 3 : MENU PRINCIPAL ─────────────────────────────────────
        while True:
            data = recevoir(client_socket)

            cookie_recu = data.get("cookie")
            with cookies_lock:
                if cookie_recu not in cookies:
                    envoyer(client_socket, {"statut": "erreur", "message": "Session invalide."})
                    break
                username = cookies[cookie_recu]

            abonne   = Abonne.get(Abonne.username == username)
            commande = data.get("commande")

            # ── Liste des vidéos ──────────────────────────────────────────
            if commande == "liste_videos":
                envoyer(client_socket, {"statut": "ok", "videos": get_liste_videos()})

            # ── Télécharger ───────────────────────────────────────────────
            elif commande == "telecharger":
                id_video = data.get("id_video")
                video    = Video.get_or_none(Video.id == id_video)

                if video is None:
                    envoyer(client_socket, {"statut": "erreur", "message": "Vidéo introuvable."})
                    continue

                # Vérification de la limite pour les Spanzo_nada
                if abonne.groupe == "Spanzo_nada":
                    maintenant = time.time()

                    # Réinitialise la fenêtre si les 15 minutes sont écoulées
                    if maintenant - abonne.telechargement_debut > FENETRE_SECONDES:
                        abonne.telechargement_mo_fenetre = 0.0
                        abonne.telechargement_debut      = maintenant

                    if abonne.telechargement_mo_fenetre + video.taille_mo > LIMITE_NADA_MO:
                        secondes_restantes = int(
                            FENETRE_SECONDES - (maintenant - abonne.telechargement_debut)
                        )
                        envoyer(client_socket, {
                            "statut": "erreur",
                            "message": (
                                f"Limite Spanzo_nada atteinte (3 Go / 15 min). "
                                f"Réessayez dans {secondes_restantes // 60} min "
                                f"{secondes_restantes % 60} s."
                            ),
                        })
                        continue

                    # Mise à jour du quota dans la fenêtre
                    abonne.telechargement_mo_fenetre += video.taille_mo
                    abonne.save()

                envoyer(client_socket, {
                    "statut"     : "ok",
                    "intitule"   : video.intitule,
                    "taille_mo"  : video.taille_mo,
                    "contenu_b64": video.contenu_b64,
                })

            # ── Téléverser ────────────────────────────────────────────────
            elif commande == "televerser":
                nom_fichier = data.get("nom_fichier", "")
                if not est_video(nom_fichier):
                    envoyer(client_socket, {
                        "statut": "erreur",
                        "message": "Fichier rejeté : pas une vidéo.",
                    })
                    continue

                contenu_b64 = data.get("contenu_b64", "")
                contenu_bin = base64.b64decode(contenu_b64)
                taille_mo   = len(contenu_bin) / (1024 * 1024)

                Video.create(
                    intitule    = data.get("intitule"),
                    description = data.get("description"),
                    taille_mo   = round(taille_mo, 2),
                    contenu_b64 = contenu_b64,
                )

                abonne.total_televerse_mo += taille_mo
                if taille_mo >= SEUIL_GOLD_MO and abonne.groupe != "Spanzo_gold":
                    abonne.nb_videos_1go += 1
                    abonne.groupe = "Spanzo_gold"
                elif taille_mo >= SEUIL_GOLD_MO:
                    # Déjà gold : on incrémente quand même le compteur
                    abonne.nb_videos_1go += 1
                abonne.save()

                envoyer(client_socket, {
                    "statut"        : "ok",
                    "message"       : f"Vidéo téléversée ! ({taille_mo:.1f} Mo)",
                    "nouveau_groupe": abonne.groupe,
                })

            # ── Quitter ───────────────────────────────────────────────────
            elif commande == "quitter":
                with cookies_lock:
                    cookies.pop(cookie_recu, None)
                cookie_session = None
                envoyer(client_socket, {"statut": "ok", "message": "À bientôt !"})
                break

            else:
                envoyer(client_socket, {"statut": "erreur", "message": "Commande inconnue."})

    except (ConnectionError, OSError) as e:
        print(f"[-] Déconnexion de {client_addr} : {e}")
    except Exception as e:
        print(f"[!] Erreur inattendue ({client_addr}) : {e}")
        try:
            envoyer(client_socket, {"statut": "erreur", "message": "Erreur interne du serveur."})
        except Exception:
            pass
    finally:
        # Nettoyage de la session en cas de déconnexion brutale
        if cookie_session is not None:
            with cookies_lock:
                cookies.pop(cookie_session, None)
        client_socket.close()
        print(f"[-] Connexion fermée : {client_addr}")


# ── Lancement du serveur ─────────────────────
tcp_socket = socket(AF_INET, SOCK_STREAM)
tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)   # évite "Address already in use"
tcp_socket.bind((HOST, PORT))
tcp_socket.listen(20)
print(f"Serveur Spanza lancé sur le port {PORT}")

while True:
    client_socket, client_addr = tcp_socket.accept()
    t = threading.Thread(
        target=traiter_client,
        args=(client_socket, client_addr),
        daemon=True,
    )
    t.start()
