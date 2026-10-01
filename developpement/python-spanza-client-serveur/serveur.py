#Diarra Babacar DIOUF
#Selbe DIOUF
#Jean Pierre Ngor SENE
#Yaye Aby SOW
#Mouhameth WADE

"""Serveur Spanza (version corrigée après revue de sécurité).

Changements par rapport à la version rendue :
  - TLS obligatoire (certificat fourni par SPANZA_CERT et SPANZA_KEY)
  - mots de passe hachés avec scrypt et un sel par utilisateur (migration des anciens SHA-256)
  - taille des messages bornée avant allocation, délai d'inactivité, nombre de clients borné
  - limitation des tentatives de connexion par adresse IP
  - cookie lié à la connexion qui l'a reçu, comparé en temps constant
  - vidéos contrôlées sur l'extension ET la signature, base64 validé, taille plafonnée
  - vidéos stockées en binaire (et non plus en base64) dans SQLite
  - quota de téléchargement protégé contre les accès concurrents
  - plus de message d'exception renvoyé au client, journalisation des événements
"""

import base64
import binascii
import hashlib
import hmac
import logging
import os
import re
import socket as socket_module
import ssl
import threading
import time
import uuid
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, socket

from peewee import (BlobField, CharField, FloatField, IntegerField, IntegrityError,
                    Model, SqliteDatabase)

from protocole import (TAILLE_MAX_AVANT_AUTH, TAILLE_MAX_MESSAGE, TAILLE_MAX_VIDEO_MO,
                       envoyer, recevoir)

log = logging.getLogger("spanza")

# ── Constantes ───────────────────────────────
SEUIL_GOLD_MO    = 1024        # 1 Go téléversé en une vidéo pour passer Spanzo_gold
LIMITE_NADA_MO   = 3 * 1024    # 3 Go
FENETRE_SECONDES = 15 * 60     # 15 minutes
EXTENSIONS_OK    = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
DELAI_INACTIVITE = 120         # secondes sans octet reçu avant de couper la connexion
MAX_CLIENTS      = 50

HOST = os.environ.get("SPANZA_HOST", "")
PORT = int(os.environ.get("SPANZA_PORT", "5000"))

RE_USERNAME = re.compile(r"[A-Za-z0-9_.-]{3,32}")

# ── Base de données ──────────────────────────
db = SqliteDatabase(None)


class Abonne(Model):
    nom                        = CharField()
    prenom                     = CharField(null=True)
    username                   = CharField(unique=True)
    password                   = CharField(max_length=200, null=False)   # scrypt$sel$hash
    groupe                     = CharField(default="Spanzo_nada")
    total_televerse_mo         = FloatField(default=0.0)
    nb_videos_1go              = IntegerField(default=0)
    telechargement_mo_fenetre  = FloatField(default=0.0)   # Mo téléchargés dans la fenêtre courante
    telechargement_debut       = FloatField(default=0.0)   # début de la fenêtre

    class Meta:
        database = db


class Video(Model):
    intitule    = CharField()
    description = CharField()
    extension   = CharField(default=".mp4")
    taille_mo   = FloatField()
    contenu     = BlobField()

    class Meta:
        database = db


def initialiser_base(chemin: str):
    db.init(chemin)
    db.connect(reuse_if_open=True)
    db.create_tables([Abonne, Video], safe=True)


quota_lock = threading.Lock()   # sérialise la lecture, le contrôle et la mise à jour des quotas


# ── Mots de passe ────────────────────────────
_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def hacher_password(password: str, sel: bytes = None) -> str:
    """Retourne 'scrypt$<sel hex>$<hash hex>' avec un sel aléatoire par mot de passe."""
    sel = sel or os.urandom(16)
    empreinte = hashlib.scrypt(password.encode("utf-8"), salt=sel, **_SCRYPT)
    return f"scrypt${sel.hex()}${empreinte.hex()}"


def verifier_password(password: str, stocke: str) -> bool:
    """Vérifie un mot de passe contre sa valeur stockée (scrypt, ou ancien SHA-256 non salé)."""
    if stocke.startswith("scrypt$"):
        try:
            _, sel_hex, hash_hex = stocke.split("$")
            attendu = bytes.fromhex(hash_hex)
            obtenu = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(sel_hex), **_SCRYPT)
        except ValueError:
            return False
        return hmac.compare_digest(obtenu, attendu)
    # Ancien format : SHA-256 hexadécimal sans sel (migré vers scrypt à la prochaine connexion)
    ancien = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(ancien, stocke)


_FAUX_HASH = hacher_password("mot de passe factice")   # même coût de calcul pour un utilisateur inconnu


# ── Limitation des tentatives de connexion ───
class LimiteurTentatives:
    """Bloque une clé (ici l'adresse IP) après trop d'échecs dans une fenêtre de temps."""

    def __init__(self, max_echecs=5, fenetre=15 * 60, blocage=15 * 60, horloge=time.monotonic):
        self.max_echecs, self.fenetre, self.blocage, self.horloge = max_echecs, fenetre, blocage, horloge
        self._echecs, self._bloque_jusqua = {}, {}
        self._verrou = threading.Lock()

    def secondes_restantes(self, cle) -> int:
        with self._verrou:
            fin = self._bloque_jusqua.get(cle, 0)
            reste = fin - self.horloge()
            if reste <= 0:
                self._bloque_jusqua.pop(cle, None)
                return 0
            return int(reste) + 1

    def echec(self, cle):
        with self._verrou:
            maintenant = self.horloge()
            recents = [t for t in self._echecs.get(cle, []) if maintenant - t < self.fenetre]
            recents.append(maintenant)
            self._echecs[cle] = recents
            if len(recents) >= self.max_echecs:
                self._bloque_jusqua[cle] = maintenant + self.blocage
                self._echecs.pop(cle, None)

    def reussite(self, cle):
        with self._verrou:
            self._echecs.pop(cle, None)


limiteur = LimiteurTentatives()


# ── Contrôles de contenu ─────────────────────
def extension_video(nom_fichier: str) -> str:
    """Retourne l'extension (minuscules) si c'est une extension vidéo autorisée, sinon ''."""
    ext = os.path.splitext(str(nom_fichier).lower())[1]
    return ext if ext in EXTENSIONS_OK else ""


def signature_valide(ext: str, contenu: bytes) -> bool:
    """Vérifie les premiers octets : l'extension seule ne prouve rien."""
    if ext in (".mp4", ".mov"):
        return contenu[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip")
    if ext in (".mkv", ".webm"):
        return contenu[:4] == b"\x1a\x45\xdf\xa3"
    if ext == ".avi":
        return contenu[:4] == b"RIFF" and contenu[8:12] == b"AVI "
    return False


def texte_valide(valeur, minimum: int, maximum: int) -> bool:
    return (isinstance(valeur, str) and minimum <= len(valeur.strip()) <= maximum
            and not any(ord(c) < 32 for c in valeur))


def get_liste_videos():
    return [
        {"id": v.id, "intitule": v.intitule, "description": v.description, "taille_mo": v.taille_mo}
        for v in Video.select()
    ]


# ── Commandes du menu principal ──────────────
def commande_telecharger(sock, abonne, data):
    video = Video.get_or_none(Video.id == data.get("id_video")) if isinstance(data.get("id_video"), int) else None
    if video is None:
        envoyer(sock, {"statut": "erreur", "message": "Vidéo introuvable."})
        return

    if abonne.groupe == "Spanzo_nada":
        with quota_lock:
            abonne = Abonne.get_by_id(abonne.id)
            maintenant = time.time()
            if maintenant - abonne.telechargement_debut > FENETRE_SECONDES:
                abonne.telechargement_mo_fenetre = 0.0
                abonne.telechargement_debut = maintenant
            if abonne.telechargement_mo_fenetre + video.taille_mo > LIMITE_NADA_MO:
                reste = int(FENETRE_SECONDES - (maintenant - abonne.telechargement_debut))
                envoyer(sock, {
                    "statut": "erreur",
                    "message": (f"Limite Spanzo_nada atteinte (3 Go / 15 min). "
                                f"Réessayez dans {reste // 60} min {reste % 60} s."),
                })
                return
            abonne.telechargement_mo_fenetre += video.taille_mo
            abonne.save()

    log.info("téléchargement vidéo %s par %s", video.id, abonne.username)
    envoyer(sock, {
        "statut": "ok",
        "id_video": video.id,
        "intitule": video.intitule,
        "extension": video.extension,
        "taille_mo": video.taille_mo,
        "contenu_b64": base64.b64encode(bytes(video.contenu)).decode("ascii"),
    })


def commande_televerser(sock, abonne, data):
    ext = extension_video(data.get("nom_fichier", ""))
    if not ext:
        envoyer(sock, {"statut": "erreur", "message": "Fichier rejeté : pas une vidéo."})
        return
    if not (texte_valide(data.get("intitule"), 1, 200) and texte_valide(data.get("description"), 0, 1000)):
        envoyer(sock, {"statut": "erreur", "message": "Intitulé ou description invalide."})
        return
    try:
        contenu = base64.b64decode(data.get("contenu_b64", ""), validate=True)
    except (binascii.Error, TypeError, ValueError):
        envoyer(sock, {"statut": "erreur", "message": "Contenu illisible."})
        return
    taille_mo = len(contenu) / (1024 * 1024)
    if taille_mo > TAILLE_MAX_VIDEO_MO:
        envoyer(sock, {"statut": "erreur", "message": f"Vidéo trop grande (maximum {TAILLE_MAX_VIDEO_MO} Mo)."})
        return
    if not signature_valide(ext, contenu):
        envoyer(sock, {"statut": "erreur", "message": "Fichier rejeté : le contenu n'est pas une vidéo valide."})
        return

    Video.create(intitule=data["intitule"].strip(), description=data["description"].strip(),
                 extension=ext, taille_mo=round(taille_mo, 2), contenu=contenu)

    with quota_lock:
        abonne = Abonne.get_by_id(abonne.id)
        abonne.total_televerse_mo += taille_mo
        if taille_mo >= SEUIL_GOLD_MO:
            abonne.nb_videos_1go += 1
            abonne.groupe = "Spanzo_gold"
        abonne.save()

    log.info("téléversement de %.1f Mo par %s", taille_mo, abonne.username)
    envoyer(sock, {"statut": "ok", "message": f"Vidéo téléversée ! ({taille_mo:.1f} Mo)",
                   "nouveau_groupe": abonne.groupe})


# ── Gestion d'un client ──────────────────────
def inscrire(sock):
    """Retourne True si l'inscription a réussi (la connexion continue alors vers l'authentification)."""
    envoyer(sock, {"__texte__": "Envoie tes données pour t'inscrire."})
    data = recevoir(sock, TAILLE_MAX_AVANT_AUTH)
    nom, prenom = data.get("nom"), data.get("prenom", "")
    username, password = data.get("username"), data.get("password")

    valide = (texte_valide(nom, 1, 100) and (prenom == "" or texte_valide(prenom, 1, 100))
              and isinstance(username, str) and RE_USERNAME.fullmatch(username)
              and isinstance(password, str) and 8 <= len(password) <= 128)
    if not valide:
        envoyer(sock, {"__texte__": "ERREUR : données invalides (username de 3 à 32 caractères "
                                    "[A-Za-z0-9_.-], mot de passe de 8 à 128 caractères)."})
        return False
    try:
        Abonne.create(nom=nom.strip(), prenom=prenom.strip(), username=username,
                      password=hacher_password(password))
    except IntegrityError:
        envoyer(sock, {"__texte__": "ERREUR : ce username est déjà pris."})
        return False
    log.info("nouvel abonné : %s", username)
    envoyer(sock, {"__texte__": "Inscription réussie ! Connecte-toi maintenant."})
    return True


def authentifier(sock, ip):
    """Retourne l'abonné authentifié, ou None après avoir répondu au client."""
    envoyer(sock, {"__texte__": "Entre ton username et ton password."})
    creds = recevoir(sock, TAILLE_MAX_AVANT_AUTH)

    reste = limiteur.secondes_restantes(ip)
    if reste:
        log.warning("connexion refusée (trop d'échecs) depuis %s", ip)
        envoyer(sock, {"cookie": "Bad password",
                       "message": f"Trop d'échecs. Réessayez dans {reste // 60 + 1} min."})
        return None

    username, password = creds.get("username"), creds.get("password")
    abonne = None
    if isinstance(username, str) and isinstance(password, str) and len(password) <= 128:
        abonne = Abonne.get_or_none(Abonne.username == username)
        stocke = abonne.password if abonne else _FAUX_HASH
        if verifier_password(password, stocke) and abonne is not None:
            if not stocke.startswith("scrypt$"):          # migration de l'ancien SHA-256 non salé
                abonne.password = hacher_password(password)
                abonne.save()
            limiteur.reussite(ip)
            return abonne
    limiteur.echec(ip)
    log.warning("échec d'authentification depuis %s", ip)
    envoyer(sock, {"cookie": "Bad password"})
    return None


def traiter_client(client_socket, client_addr, contexte_tls=None, slot=None):
    ip = client_addr[0]
    log.info("connexion de %s", client_addr)
    try:
        if contexte_tls is not None:
            client_socket = contexte_tls.wrap_socket(client_socket, server_side=True)
        client_socket.settimeout(DELAI_INACTIVITE)

        envoyer(client_socket, {"__texte__": "Bienvenue sur Spanza ! Tapez 'inscription' ou 'connexion'."})
        choix = str(recevoir(client_socket, TAILLE_MAX_AVANT_AUTH).get("choix", "")).strip().lower()

        if choix == "inscription":
            if not inscrire(client_socket):
                return
        elif choix != "connexion":
            envoyer(client_socket, {"__texte__": "Choix invalide. Au revoir."})
            return

        abonne = authentifier(client_socket, ip)
        if abonne is None:
            return

        cookie_session = str(uuid.uuid4())
        envoyer(client_socket, {"cookie": cookie_session})
        log.info("[%s] connecté en tant que '%s'", ip, abonne.username)

        while True:
            data = recevoir(client_socket, TAILLE_MAX_MESSAGE)
            cookie_recu = data.get("cookie")
            if not (isinstance(cookie_recu, str)
                    and hmac.compare_digest(cookie_recu.encode("utf-8"), cookie_session.encode("utf-8"))):
                envoyer(client_socket, {"statut": "erreur", "message": "Session invalide."})
                break

            abonne = Abonne.get_by_id(abonne.id)
            commande = data.get("commande")
            if commande == "liste_videos":
                envoyer(client_socket, {"statut": "ok", "videos": get_liste_videos()})
            elif commande == "telecharger":
                commande_telecharger(client_socket, abonne, data)
            elif commande == "televerser":
                commande_televerser(client_socket, abonne, data)
            elif commande == "quitter":
                envoyer(client_socket, {"statut": "ok", "message": "À bientôt !"})
                break
            else:
                envoyer(client_socket, {"statut": "erreur", "message": "Commande inconnue."})

    except (ConnectionError, OSError, ssl.SSLError, socket_module.timeout) as e:
        log.info("déconnexion de %s : %s", client_addr, e)
    except Exception:
        log.exception("erreur inattendue (%s)", client_addr)
        try:
            envoyer(client_socket, {"statut": "erreur", "message": "Erreur interne du serveur."})
        except Exception:
            pass
    finally:
        try:
            client_socket.close()
        except OSError:
            pass
        if not db.is_closed():          # connexion SQLite propre à ce thread
            db.close()
        if slot is not None:
            slot.release()
        log.info("connexion fermée : %s", client_addr)


# ── Lancement du serveur ─────────────────────
def creer_contexte_tls():
    cert, cle = os.environ.get("SPANZA_CERT"), os.environ.get("SPANZA_KEY")
    if cert and cle:
        contexte = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexte.minimum_version = ssl.TLSVersion.TLSv1_2
        contexte.load_cert_chain(cert, cle)
        return contexte
    if os.environ.get("SPANZA_ALLOW_PLAINTEXT") == "1":
        log.warning("TLS DÉSACTIVÉ : mots de passe et vidéos circulent en clair. Laboratoire uniquement.")
        return None
    raise SystemExit("TLS requis : définir SPANZA_CERT et SPANZA_KEY "
                     "(voir le README), ou SPANZA_ALLOW_PLAINTEXT=1 en laboratoire.")


def servir(tcp_socket, contexte_tls=None, arret: threading.Event = None):
    """Boucle d'acceptation. S'arrête quand `arret` est positionné (utilisé par les tests)."""
    places = threading.BoundedSemaphore(MAX_CLIENTS)
    tcp_socket.settimeout(0.5)
    while arret is None or not arret.is_set():
        try:
            client_socket, client_addr = tcp_socket.accept()
        except socket_module.timeout:
            continue
        except OSError:
            break
        if not places.acquire(blocking=False):
            log.warning("trop de clients simultanés, connexion de %s refusée", client_addr)
            client_socket.close()
            continue
        threading.Thread(target=traiter_client, args=(client_socket, client_addr, contexte_tls, places),
                         daemon=True).start()


def creer_socket_serveur(host, port):
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcp_socket.bind((host, port))
    tcp_socket.listen(20)
    return tcp_socket


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    initialiser_base(os.environ.get("SPANZA_DB", "spanza.db"))
    contexte = creer_contexte_tls()
    tcp_socket = creer_socket_serveur(HOST, PORT)
    log.info("Serveur Spanza lancé sur le port %s (%s)", PORT, "TLS" if contexte else "SANS TLS")
    servir(tcp_socket, contexte)


if __name__ == "__main__":
    main()
