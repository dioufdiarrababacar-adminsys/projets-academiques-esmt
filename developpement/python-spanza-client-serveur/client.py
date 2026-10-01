#Diarra Babacar DIOUF
#Selbe DIOUF
#Jean Pierre Ngor SENE
#Yaye Aby SOW
#Mouhameth WADE


import base64
import os
import getpass
from json import dumps, loads
from socket import AF_INET, SOCK_STREAM, socket

HOTE = "192.168.1.18"   # Adresse IP du serveur
PORT = 5000

# Cookie de session (reçu après connexion)
mon_cookie = None


# ── Protocole de communication (longueur préfixée) ──────────────────────────
# Miroir exact du protocole côté serveur : 4 octets big-endian + payload JSON.

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
            raise ConnectionError("Le serveur a fermé la connexion.")
        entete += chunk

    longueur = int.from_bytes(entete, "big")

    # Lire exactement longueur octets
    data = b""
    while len(data) < longueur:
        chunk = sock.recv(min(65536, longueur - len(data)))
        if not chunk:
            raise ConnectionError("Connexion perdue pendant la réception.")
        data += chunk

    return loads(data.decode("utf-8"))


def afficher_message_serveur(rep: dict):
    """Affiche le champ __texte__ ou message d'une réponse serveur."""
    texte = rep.get("__texte__") or rep.get("message", "")
    if texte:
        print(">>", texte)


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

def inscription(sock):
    rep = recevoir(sock)
    afficher_message_serveur(rep)

    nom      = input("Nom      : ")
    prenom   = input("Prénom   : ")
    username = input("Username : ")
    password = getpass.getpass("Password : ")

    envoyer(sock, {
        "nom"     : nom,
        "prenom"  : prenom,
        "username": username,
        "password": password,
    })

    rep = recevoir(sock)
    afficher_message_serveur(rep)

    # Si le username est déjà pris, le serveur envoie une erreur et ferme
    if "ERREUR" in rep.get("__texte__", ""):
        return False
    return True


# ── CONNEXION (reçoit le cookie) ─────────────────────────────────────────────

def connexion(sock) -> bool:
    global mon_cookie

    rep = recevoir(sock)
    afficher_message_serveur(rep)

    username = input("Username : ")
    password = getpass.getpass("Password : ")

    envoyer(sock, {"username": username, "password": password})

    rep = recevoir(sock)
    cookie_recu = rep.get("cookie")

    if cookie_recu == "Bad password" or cookie_recu is None:
        print(">> Mauvais identifiant ou mot de passe. Connexion refusée.")
        return False

    mon_cookie = cookie_recu
    print(f">> Connecté ! (session : {mon_cookie[:8]}...)")
    return True


# ── LISTE DES VIDÉOS ─────────────────────────────────────────────────────────

def liste_videos(sock):
    envoyer(sock, {"cookie": mon_cookie, "commande": "liste_videos"})
    rep = recevoir(sock)

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

    envoyer(sock, {
        "cookie"  : mon_cookie,
        "commande": "telecharger",
        "id_video": int(id_video),
    })

    rep = recevoir(sock)

    if rep.get("statut") != "ok":
        print(">> Erreur :", rep.get("message"))
        return

    contenu_b64 = rep.get("contenu_b64", "")
    if contenu_b64:
        os.makedirs("telechargements", exist_ok=True)
        nom_fichier = os.path.join(
            "telechargements",
            rep["intitule"].replace(" ", "_") + ".mp4",
        )
        with open(nom_fichier, "wb") as f:
            f.write(base64.b64decode(contenu_b64))
        print(f">> Vidéo enregistrée : {nom_fichier} ({rep['taille_mo']} Mo)")
    else:
        print(f">> Téléchargement autorisé ({rep['taille_mo']} Mo) — pas de contenu binaire.")


# ── TÉLÉVERSER ───────────────────────────────────────────────────────────────

def televerser(sock):
    chemin = input("Chemin du fichier vidéo : ").strip()
    if not os.path.exists(chemin):
        print("Fichier introuvable.")
        return

    intitule    = input("Intitulé    : ")
    description = input("Description : ")
    nom_fichier = os.path.basename(chemin)

    print("Lecture et encodage en cours...")
    with open(chemin, "rb") as f:
        contenu_b64 = base64.b64encode(f.read()).decode("ascii")

    print("Envoi au serveur (cela peut prendre quelques instants)...")
    envoyer(sock, {
        "cookie"     : mon_cookie,
        "commande"   : "televerser",
        "nom_fichier": nom_fichier,
        "intitule"   : intitule,
        "description": description,
        "contenu_b64": contenu_b64,
    })

    rep = recevoir(sock)
    print(">>", rep.get("message"))
    if rep.get("nouveau_groupe"):
        print(f"   Votre groupe : {rep['nouveau_groupe']}")


# ── QUITTER ──────────────────────────────────────────────────────────────────

def quitter(sock):
    envoyer(sock, {"cookie": mon_cookie, "commande": "quitter"})
    rep = recevoir(sock)
    print(">>", rep.get("message"))


# ── PROGRAMME PRINCIPAL ──────────────────────────────────────────────────────

def main():
    global mon_cookie

    sock = socket(AF_INET, SOCK_STREAM)
    try:
        sock.connect((HOTE, PORT))
    except ConnectionRefusedError:
        print(f"Impossible de se connecter à {HOTE}:{PORT}")
        print("Vérifiez que le serveur est bien lancé.")
        return

    print("Connecté au serveur Spanza !")

    try:
        # ── Étape 1 : Inscription ou connexion ──
        mode = choisir_mode(sock)

        if mode == "inscription":
            ok = inscription(sock)
            if not ok:
                return
            # Après inscription, le serveur attend maintenant la connexion
            # (il envoie le prompt d'authentification)

        # ── Étape 2 : Authentification ──
        connecte = connexion(sock)
        if not connecte:
            return
        # ── Étape 3 : Menu principal ──

        while True:
            print("\n*************************************")
            print("      🎥 VIDEOTHEQUE SPANZA - MENU      ")
            print("========================================")
            if mon_cookie:
                print(f" Connecté (session : {mon_cookie[:8]}...)")
            else:
                print(" Aucun utilisateur connecté actuellement.")
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


    except ConnectionError as e:
        print(f"\n[!] Connexion perdue : {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
