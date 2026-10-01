"""Protocole de communication Spanza : JSON préfixé par sa longueur.

Chaque message est précédé de 4 octets (big-endian) indiquant la taille du JSON.
Le récepteur refuse tout message plus grand que la limite qu'il s'est fixée, avant
d'allouer quoi que ce soit : un client ne peut plus saturer la mémoire du serveur
en annonçant une longueur démesurée.
"""

from json import dumps, loads

TAILLE_MAX_AVANT_AUTH = 64 * 1024            # 64 Kio : inscription, connexion
TAILLE_MAX_MESSAGE = 1024 * 1024 * 1024      # 1 Gio : messages authentifiés (vidéos en base64)
TAILLE_MAX_VIDEO_MO = 700                    # 700 Mo de vidéo font ~933 Mo en base64, sous la limite ci-dessus

_BLOC_LECTURE = 256 * 1024


class MessageInvalide(ConnectionError):
    """Message trop grand, mal formé ou qui n'est pas un objet JSON."""


def envoyer(sock, dico: dict):
    """Sérialise dico en JSON et l'envoie avec un préfixe de longueur de 4 octets."""
    data = dumps(dico, ensure_ascii=False).encode("utf-8")
    if len(data) > 0xFFFFFFFF:
        raise ValueError("Message trop grand pour le protocole.")
    sock.sendall(len(data).to_bytes(4, "big"))
    sock.sendall(data)


def _lire_exactement(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(_BLOC_LECTURE, n - len(buf)))
        if not chunk:
            raise ConnectionError("Connexion fermée par le correspondant.")
        buf += chunk
    return bytes(buf)


def recevoir(sock, max_taille: int = TAILLE_MAX_MESSAGE) -> dict:
    """Reçoit un message préfixé par sa longueur ; refuse tout message > max_taille."""
    longueur = int.from_bytes(_lire_exactement(sock, 4), "big")
    if longueur > max_taille:
        raise MessageInvalide(f"Message de {longueur} octets refusé (maximum {max_taille}).")
    data = _lire_exactement(sock, longueur)
    try:
        message = loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise MessageInvalide("Message JSON illisible.")
    if not isinstance(message, dict):
        raise MessageInvalide("Un message doit être un objet JSON.")
    return message
