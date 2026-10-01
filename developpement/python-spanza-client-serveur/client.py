#Diarra Babacar DIOUF
#Selbe DIOUF
#Jean Pierre Ngor SENE
#Yaye Aby SOW
#Mouhameth WADE

"""Client Spanza (version corrigée après revue de sécurité).

Changements par rapport à la version rendue :
  - connexion chiffrée en TLS, avec vérification du certificat du serveur
  - adresse et port du serveur en paramètres (plus d'IP codée en dur)
  - le nom du fichier téléchargé ne vient plus tel quel de l'intitulé choisi par un autre
    abonné : un intitulé comme '../../x' ne peut plus écrire hors du dossier telechargements
  - extension du fichier fournie par le serveur, contenu base64 validé
  - taille du fichier contrôlée avant de le lire en mémoire
"""

import argparse
import base64
import binascii
import getpass
import os
import re
import ssl
from socket import AF_INET, SOCK_STREAM, socket

from protocole import TAILLE_MAX_MESSAGE, TAILLE_MAX_VIDEO_MO, envoyer, recevoir

EXTENSIONS_OK = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
DOSSIER_TELECHARGEMENTS = "telechargements"

# Cookie de session (reçu après connexion)
mon_cookie = None


def afficher_message_serveur(rep: dict):
    """Affiche le champ __texte__ ou message d'une réponse serveur."""
    texte = rep.get("__texte__") or rep.get("message", "")
    if texte:
        print(">>", texte)


def nom_fichier_sur(intitule, id_video, extension) -> str:
    """Construit un nom de fichier sûr : uniquement [A-Za-z0-9._-], jamais de séparateur de chemin."""
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", str(intitule)).strip("._")[:80] or "video"
    ext = extension if extension in EXTENSIONS_OK else ".mp4"
    return f"{int(id_video)}_{base}{ext}"


# ── CHOIX INSCRIPTION / CONNEXION ────────────────────────────────────────────

def choisir_mode(sock) -> str:
    """Affiche le menu d'accueil et retourne 'inscription' ou 'connexion'."""
    rep = recevoir(sock)
    afficher_message_serveur(rep)

    while True:
        choix = input("Votre choix (inscription / connexion) : ").strip().lower()
        if choix in ("inscription", "connexion"):
            envoyer(sock, {"choix": choix})
            return choix
        print("Tapez 'inscription' ou 'connexion'.")


# ── INSCRIPTION ──────────────────────────────────────────────────────────────

def inscription(sock) -> bool:
    afficher_message_serveur(recevoir(sock))

    nom      = input("Nom      : ")
    prenom   = input("Prénom   : ")
    username = input("Username : ")
    password = getpass.getpass("Password (8 caractères minimum) : ")

    envoyer(sock, {"nom": nom, "prenom": prenom, "username": username, "password": password})

    rep = recevoir(sock)
    afficher_message_serveur(rep)
    return "ERREUR" not in rep.get("__texte__", "")


# ── CONNEXION (reçoit le cookie) ─────────────────────────────────────────────

def connexion(sock) -> bool:
    global mon_cookie

    afficher_message_serveur(recevoir(sock))

    username = input("Username : ")
    password = getpass.getpass("Password : ")
    envoyer(sock, {"username": username, "password": password})

    rep = recevoir(sock)
    cookie_recu = rep.get("cookie")

    if not isinstance(cookie_recu, str) or cookie_recu == "Bad password":
        print(">>", rep.get("message") or "Mauvais identifiant ou mot de passe. Connexion refusée.")
        return False

    mon_cookie = cookie_recu
    print(f">> Connecté ! (session : {mon_cookie[:8]}...)")
    return True


# ── LISTE DES VIDÉOS ─────────────────────────────────────────────────────────

def liste_videos(sock):
    envoyer(sock, {"cookie": mon_cookie, "commande": "liste_videos"})
    rep = recevoir(sock, TAILLE_MAX_MESSAGE)

    if rep.get("statut") != "ok":
        print(">> Erreur :", rep.get("message"))
        return

    videos = rep.get("videos", [])
    if not videos:
        print("   (Aucune vidéo disponible pour le moment.)")
        return

    print("\n   --- Vidéos disponibles ---")
    for v in videos:
        print(f"   [{v['id']}] {v['intitule']}  —  {v['taille_mo']} Mo")
        print(f"        {v['description']}")


# ── TÉLÉCHARGER ──────────────────────────────────────────────────────────────

def telecharger(sock):
    id_video = input("ID de la vidéo à télécharger : ").strip()
    if not id_video.isdigit():
        print("ID invalide.")
        return

    envoyer(sock, {"cookie": mon_cookie, "commande": "telecharger", "id_video": int(id_video)})
    rep = recevoir(sock, TAILLE_MAX_MESSAGE)

    if rep.get("statut") != "ok":
        print(">> Erreur :", rep.get("message"))
        return

    try:
        contenu = base64.b64decode(rep.get("contenu_b64", ""), validate=True)
    except (binascii.Error, ValueError):
        print(">> Erreur : contenu reçu illisible.")
        return

    os.makedirs(DOSSIER_TELECHARGEMENTS, exist_ok=True)
    chemin = os.path.join(DOSSIER_TELECHARGEMENTS,
                          nom_fichier_sur(rep.get("intitule", ""), rep.get("id_video", id_video),
                                          rep.get("extension", ".mp4")))
    with open(chemin, "wb") as f:
        f.write(contenu)
    print(f">> Vidéo enregistrée : {chemin} ({rep.get('taille_mo')} Mo)")


# ── TÉLÉVERSER ───────────────────────────────────────────────────────────────

def televerser(sock):
    chemin = input("Chemin du fichier vidéo : ").strip()
    if not os.path.isfile(chemin):
        print("Fichier introuvable.")
        return
    if os.path.getsize(chemin) > TAILLE_MAX_VIDEO_MO * 1024 * 1024:
        print(f"Fichier trop grand (maximum {TAILLE_MAX_VIDEO_MO} Mo).")
        return

    intitule    = input("Intitulé    : ")
    description = input("Description : ")

    print("Lecture et encodage en cours...")
    with open(chemin, "rb") as f:
        contenu_b64 = base64.b64encode(f.read()).decode("ascii")

    print("Envoi au serveur (cela peut prendre quelques instants)...")
    envoyer(sock, {
        "cookie"     : mon_cookie,
        "commande"   : "televerser",
        "nom_fichier": os.path.basename(chemin),
        "intitule"   : intitule,
        "description": description,
        "contenu_b64": contenu_b64,
    })

    rep = recevoir(sock, TAILLE_MAX_MESSAGE)
    print(">>", rep.get("message"))
    if rep.get("nouveau_groupe"):
        print(f"   Votre groupe : {rep['nouveau_groupe']}")


# ── QUITTER ──────────────────────────────────────────────────────────────────

def quitter(sock):
    envoyer(sock, {"cookie": mon_cookie, "commande": "quitter"})
    print(">>", recevoir(sock).get("message"))


# ── PROGRAMME PRINCIPAL ──────────────────────────────────────────────────────

def lire_arguments():
    p = argparse.ArgumentParser(description="Client Spanza")
    p.add_argument("--hote", default=os.environ.get("SPANZA_HOTE", "127.0.0.1"), help="adresse du serveur")
    p.add_argument("--port", type=int, default=int(os.environ.get("SPANZA_PORT", "5000")))
    p.add_argument("--ca", default=os.environ.get("SPANZA_CA"),
                   help="certificat du serveur (ou de son autorité) à utiliser pour vérifier la connexion TLS")
    p.add_argument("--sans-tls", action="store_true",
                   help="connexion en clair (laboratoire uniquement, le serveur doit l'autoriser)")
    return p.parse_args()


def ouvrir_connexion(args):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((args.hote, args.port))
    if args.sans_tls:
        print("[!] Connexion NON chiffrée : mots de passe et vidéos circulent en clair.")
        return sock
    contexte = ssl.create_default_context(cafile=args.ca)   # vérifie le certificat et le nom d'hôte
    return contexte.wrap_socket(sock, server_hostname=args.hote)


def menu(sock):
    while True:
        print("\n*************************************")
        print("      🎥 VIDEOTHEQUE SPANZA - MENU      ")
        print("========================================")
        print(f" Connecté (session : {mon_cookie[:8]}...)")
        print("----------------------------------------")
        print("1. Consulter le catalogue des vidéos")
        print("2. Télécharger une vidéo")
        print("3. Téléverser une vidéo")
        print("4. Quitter l'application")
        print("========================================")
        choix = input("Votre choix : ").strip()

        if choix == "1":
            liste_videos(sock)
        elif choix == "2":
            telecharger(sock)
        elif choix == "3":
            televerser(sock)
        elif choix == "4":
            quitter(sock)
            break
        else:
            print("Choix invalide.")


def main():
    args = lire_arguments()
    try:
        sock = ouvrir_connexion(args)
    except ConnectionRefusedError:
        print(f"Impossible de se connecter à {args.hote}:{args.port}")
        print("Vérifiez que le serveur est bien lancé.")
        return
    except ssl.SSLError as e:
        print(f"Connexion TLS refusée : {e}")
        print("Vérifiez --ca (certificat du serveur) et que l'adresse correspond à celle du certificat.")
        return

    print("Connecté au serveur Spanza !")
    try:
        mode = choisir_mode(sock)
        if mode == "inscription" and not inscription(sock):
            return
        if not connexion(sock):
            return
        menu(sock)
    except ConnectionError as e:
        print(f"\n[!] Connexion perdue : {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
