"""Tests d'intégration de Spanza : un vrai serveur TLS sur localhost, une base SQLite temporaire.

Lancer depuis le dossier du projet :  python -m unittest discover -s tests -v
Nécessite la commande `openssl` (pour fabriquer un certificat de test).
"""

import base64
import os
import shutil
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from socket import AF_INET, SOCK_STREAM, socket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import client      # noqa: E402
import protocole   # noqa: E402
import serveur     # noqa: E402

MP4_MINIMAL = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40


def faux_mp4(taille_octets):
    return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * (taille_octets - 12)


@unittest.skipUnless(shutil.which("openssl"), "openssl absent")
class TestSpanza(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp()
        cert, cle = os.path.join(cls.dossier, "cert.pem"), os.path.join(cls.dossier, "cle.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", cle, "-out", cert,
                        "-days", "1", "-subj", "/CN=localhost",
                        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                       check=True, capture_output=True)
        cls.cert = cert
        serveur.initialiser_base(os.path.join(cls.dossier, "test.db"))
        contexte = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexte.load_cert_chain(cert, cle)
        cls.tcp = serveur.creer_socket_serveur("127.0.0.1", 0)
        cls.port = cls.tcp.getsockname()[1]
        cls.arret = threading.Event()
        cls.fil = threading.Thread(target=serveur.servir, args=(cls.tcp, contexte, cls.arret), daemon=True)
        cls.fil.start()

    @classmethod
    def tearDownClass(cls):
        cls.arret.set()
        cls.fil.join(3)
        cls.tcp.close()
        serveur.db.close()
        shutil.rmtree(cls.dossier, ignore_errors=True)

    def setUp(self):
        serveur.limiteur = serveur.LimiteurTentatives()
        self.sockets = []

    def tearDown(self):
        for s in self.sockets:
            s.close()

    # ── outils ──
    def ouvrir(self, tls=True):
        brut = socket(AF_INET, SOCK_STREAM)
        brut.settimeout(10)
        brut.connect(("127.0.0.1", self.port))
        if not tls:
            self.sockets.append(brut)
            return brut
        contexte = ssl.create_default_context(cafile=self.cert)
        s = contexte.wrap_socket(brut, server_hostname="localhost")
        self.sockets.append(s)
        return s

    def inscrire(self, username, password="motdepasse8", nom="Nom"):
        s = self.ouvrir()
        protocole.recevoir(s)
        protocole.envoyer(s, {"choix": "inscription"})
        protocole.recevoir(s)
        protocole.envoyer(s, {"nom": nom, "prenom": "P", "username": username, "password": password})
        rep = protocole.recevoir(s)
        s.close()
        return rep["__texte__"]

    def connecter(self, username, password="motdepasse8"):
        """Retourne (socket, cookie) ou (socket, None) si refusé."""
        s = self.ouvrir()
        protocole.recevoir(s)
        protocole.envoyer(s, {"choix": "connexion"})
        protocole.recevoir(s)
        protocole.envoyer(s, {"username": username, "password": password})
        rep = protocole.recevoir(s)
        cookie = rep.get("cookie")
        return s, (None if cookie == "Bad password" else cookie), rep

    def cmd(self, s, cookie, **kw):
        protocole.envoyer(s, {"cookie": cookie, **kw})
        return protocole.recevoir(s)

    def televerser(self, s, cookie, contenu=MP4_MINIMAL, nom="v.mp4", intitule="Mon titre"):
        return self.cmd(s, cookie, commande="televerser", nom_fichier=nom, intitule=intitule,
                        description="d", contenu_b64=base64.b64encode(contenu).decode())

    # ── transport ──
    def test_connexion_en_clair_refusee(self):
        s = self.ouvrir(tls=False)
        s.sendall(b"\x00\x00\x00\x02{}")           # un client sans TLS ne doit rien obtenir d'exploitable
        try:
            donnees = s.recv(100)
        except (ConnectionError, OSError):
            donnees = b""
        self.assertNotIn(b"Bienvenue", donnees)

    def test_message_geant_refuse_sans_allocation(self):
        s = self.ouvrir()
        protocole.recevoir(s)
        s.sendall(struct.pack(">I", 2 * 1024 ** 3))   # annonce 2 Gio avant authentification
        self.assertEqual(s.recv(10), b"")             # le serveur coupe la connexion

    def test_json_invalide_coupe_la_connexion(self):
        s = self.ouvrir()
        protocole.recevoir(s)
        s.sendall(struct.pack(">I", 5) + b"[1,2]")    # JSON valide mais pas un objet
        self.assertEqual(s.recv(10), b"")

    # ── inscription et connexion ──
    def test_inscription_et_doublon(self):
        self.assertIn("réussie", self.inscrire("alice_1"))
        self.assertIn("déjà pris", self.inscrire("alice_1"))

    def test_inscription_donnees_invalides(self):
        self.assertIn("ERREUR", self.inscrire("a", "motdepasse8"))          # username trop court
        self.assertIn("ERREUR", self.inscrire("bob_ok", "court"))           # mot de passe trop court
        self.assertIn("ERREUR", self.inscrire("bad name!", "motdepasse8"))  # caractères interdits

    def test_mot_de_passe_stocke_hache_avec_sel(self):
        self.inscrire("sel_1", "memeMotDePasse")
        self.inscrire("sel_2", "memeMotDePasse")
        h1 = serveur.Abonne.get(serveur.Abonne.username == "sel_1").password
        h2 = serveur.Abonne.get(serveur.Abonne.username == "sel_2").password
        self.assertTrue(h1.startswith("scrypt$"))
        self.assertNotEqual(h1, h2)                       # même mot de passe, hachages différents
        self.assertNotIn("memeMotDePasse", h1)

    def test_connexion_bon_et_mauvais_mot_de_passe(self):
        self.inscrire("carol")
        _, cookie, _ = self.connecter("carol", "mauvais")
        self.assertIsNone(cookie)
        _, cookie, _ = self.connecter("inconnu", "motdepasse8")
        self.assertIsNone(cookie)
        _, cookie, _ = self.connecter("carol")
        self.assertIsNotNone(cookie)

    def test_limitation_des_tentatives(self):
        self.inscrire("dave")
        for _ in range(5):
            self.assertIsNone(self.connecter("dave", "faux")[1])
        _, cookie, rep = self.connecter("dave")           # le bon mot de passe est maintenant refusé aussi
        self.assertIsNone(cookie)
        self.assertIn("Trop d'échecs", rep.get("message", ""))

    def test_migration_ancien_hash_sha256(self):
        import hashlib
        serveur.Abonne.create(nom="Old", prenom="", username="ancien",
                              password=hashlib.sha256(b"vieuxmotdepasse").hexdigest())
        _, cookie, _ = self.connecter("ancien", "vieuxmotdepasse")
        self.assertIsNotNone(cookie)
        self.assertTrue(serveur.Abonne.get(serveur.Abonne.username == "ancien").password.startswith("scrypt$"))

    # ── session ──
    def test_cookie_invalide_refuse(self):
        self.inscrire("erin")
        s, cookie, _ = self.connecter("erin")
        rep = self.cmd(s, "cookie-volé", commande="liste_videos")
        self.assertEqual(rep["statut"], "erreur")

    def test_cookie_non_ascii_ne_provoque_pas_d_erreur_interne(self):
        self.inscrire("elsa")
        s, cookie, _ = self.connecter("elsa")
        rep = self.cmd(s, "cookié-é€", commande="liste_videos")
        self.assertEqual(rep["statut"], "erreur")
        self.assertEqual(rep["message"], "Session invalide.")     # et non « Erreur interne du serveur »

    def test_cookie_lie_a_la_connexion(self):
        """Le cookie d'une connexion ne sert à rien sur une autre connexion, même authentifiée."""
        self.inscrire("frank")
        self.inscrire("frida")
        _, cookie_frank, _ = self.connecter("frank")
        s_frida, cookie_frida, _ = self.connecter("frida")
        rep = self.cmd(s_frida, cookie_frank, commande="liste_videos")
        self.assertEqual(rep["statut"], "erreur")
        self.assertEqual(rep["message"], "Session invalide.")

    # ── vidéos ──
    def test_televersement_telechargement_identiques(self):
        self.inscrire("gina")
        s, cookie, _ = self.connecter("gina")
        rep = self.televerser(s, cookie, faux_mp4(5000), intitule="Ma vidéo")
        self.assertEqual(rep["statut"], "ok")
        self.assertEqual(rep["nouveau_groupe"], "Spanzo_nada")
        videos = self.cmd(s, cookie, commande="liste_videos")["videos"]
        id_video = [v["id"] for v in videos if v["intitule"] == "Ma vidéo"][0]
        dl = self.cmd(s, cookie, commande="telecharger", id_video=id_video)
        self.assertEqual(dl["statut"], "ok")
        self.assertEqual(base64.b64decode(dl["contenu_b64"]), faux_mp4(5000))
        self.assertEqual(dl["extension"], ".mp4")

    def test_televersement_refuse(self):
        self.inscrire("hugo")
        s, cookie, _ = self.connecter("hugo")
        self.assertEqual(self.televerser(s, cookie, nom="virus.exe")["statut"], "erreur")            # extension
        self.assertEqual(self.televerser(s, cookie, b"MZ" + b"\x00" * 100)["statut"], "erreur")      # exe renommé en .mp4
        rep = self.cmd(s, cookie, commande="televerser", nom_fichier="v.mp4", intitule="t",
                       description="d", contenu_b64="pas du base64 !!!")
        self.assertEqual(rep["statut"], "erreur")                                                    # base64 invalide
        rep = self.cmd(s, cookie, commande="televerser", nom_fichier="v.mp4", intitule=None,
                       description="d", contenu_b64=base64.b64encode(MP4_MINIMAL).decode())
        self.assertEqual(rep["statut"], "erreur")                                                    # intitulé absent
        rep = self.cmd(s, cookie, commande="telecharger", id_video="1; DROP TABLE video")
        self.assertEqual(rep["statut"], "erreur")                                                    # id non entier

    def test_passage_gold(self):
        ancien = serveur.SEUIL_GOLD_MO
        serveur.SEUIL_GOLD_MO = 0.001                      # 1 Ko au lieu de 1 Go, pour tester la règle
        try:
            self.inscrire("iris")
            s, cookie, _ = self.connecter("iris")
            self.assertEqual(self.televerser(s, cookie, faux_mp4(5000))["nouveau_groupe"], "Spanzo_gold")
        finally:
            serveur.SEUIL_GOLD_MO = ancien

    def test_quota_spanzo_nada(self):
        ancien = serveur.LIMITE_NADA_MO
        serveur.LIMITE_NADA_MO = 1.5                       # 1,5 Mo au lieu de 3 Go
        try:
            self.inscrire("jules")
            s, cookie, _ = self.connecter("jules")
            self.televerser(s, cookie, faux_mp4(1024 * 1024), intitule="Un Mo")
            id_video = [v["id"] for v in self.cmd(s, cookie, commande="liste_videos")["videos"]
                        if v["intitule"] == "Un Mo"][0]
            self.assertEqual(self.cmd(s, cookie, commande="telecharger", id_video=id_video)["statut"], "ok")
            rep = self.cmd(s, cookie, commande="telecharger", id_video=id_video)
            self.assertEqual(rep["statut"], "erreur")
            self.assertIn("Limite Spanzo_nada", rep["message"])
        finally:
            serveur.LIMITE_NADA_MO = ancien


    # ── le vrai client.py (entrées simulées) contre le vrai serveur TLS ──
    def test_parcours_complet_avec_titre_hostile(self):
        from types import SimpleNamespace
        from unittest import mock

        src = os.path.join(self.dossier, "source.mp4")
        with open(src, "wb") as f:
            f.write(faux_mp4(3000))
        cwd = os.getcwd()
        os.chdir(self.dossier)                         # le client écrit dans ./telechargements
        try:
            args = SimpleNamespace(hote="localhost", port=self.port, ca=self.cert, sans_tls=False)
            sock = client.ouvrir_connexion(args)
            self.sockets.append(sock)
            saisies = iter(["inscription", "Nom", "Prenom", "kevin", "kevin"])
            with mock.patch("builtins.input", lambda *_: next(saisies)), \
                 mock.patch("client.getpass.getpass", side_effect=["motdepasse8", "mauvais-mot-de-passe"]):
                client.choisir_mode(sock)
                self.assertTrue(client.inscription(sock))
                # mauvais mot de passe saisi volontairement : la connexion doit être refusée proprement
                self.assertFalse(client.connexion(sock))
        finally:
            os.chdir(cwd)

        # deuxième session, avec le bon mot de passe, pour le parcours complet
        os.chdir(self.dossier)
        try:
            sock = client.ouvrir_connexion(args)
            self.sockets.append(sock)
            # choisir_mode, connexion (username), televerser (chemin, intitulé, description), telecharger (id)
            saisies = iter(["connexion", "kevin", src, "../../evil", "une description", "ID"])
            id_a_telecharger = {}

            def entree(*_):
                valeur = next(saisies)
                if valeur == "ID":
                    return str(id_a_telecharger["id"])
                return valeur

            with mock.patch("builtins.input", entree), mock.patch("client.getpass.getpass", return_value="motdepasse8"):
                client.choisir_mode(sock)
                self.assertTrue(client.connexion(sock))
                client.televerser(sock)
                videos = self.cmd(sock, client.mon_cookie, commande="liste_videos")["videos"]
                id_a_telecharger["id"] = [v["id"] for v in videos if v["intitule"] == "../../evil"][0]
                client.liste_videos(sock)
                client.telecharger(sock)
                client.quitter(sock)
            fichiers = os.listdir(os.path.join(self.dossier, "telechargements"))
            self.assertEqual(len(fichiers), 1)
            self.assertTrue(fichiers[0].endswith("_evil.mp4"), fichiers)
            with open(os.path.join(self.dossier, "telechargements", fichiers[0]), "rb") as f:
                self.assertEqual(f.read(), faux_mp4(3000))
            self.assertFalse(os.path.exists(os.path.join(self.dossier, "..", "..", "evil.mp4")))
        finally:
            os.chdir(cwd)


class TestClient(unittest.TestCase):
    def test_nom_fichier_sur_bloque_la_traversee_de_chemin(self):
        for hostile in ("../../etc/passwd", "..\\..\\Windows\\x", "/abs/chemin", "a/b\\c", "..", "", "con:aux"):
            nom = client.nom_fichier_sur(hostile, 7, ".mp4")
            self.assertEqual(os.path.basename(nom), nom, hostile)
            self.assertNotIn("/", nom)
            self.assertNotIn("\\", nom)
            self.assertTrue(nom.startswith("7_"))

    def test_extension_inconnue_remplacee(self):
        self.assertTrue(client.nom_fichier_sur("x", 1, ".exe").endswith(".mp4"))
        self.assertTrue(client.nom_fichier_sur("x", 1, ".mkv").endswith(".mkv"))


class TestSignaturesEtLimiteur(unittest.TestCase):
    def test_signatures(self):
        self.assertTrue(serveur.signature_valide(".mp4", MP4_MINIMAL))
        self.assertTrue(serveur.signature_valide(".mkv", b"\x1a\x45\xdf\xa3" + b"\x00" * 8))
        self.assertTrue(serveur.signature_valide(".avi", b"RIFF\x00\x00\x00\x00AVI LIST"))
        self.assertFalse(serveur.signature_valide(".mp4", b"MZ" + b"\x00" * 20))
        self.assertFalse(serveur.signature_valide(".avi", b"RIFF\x00\x00\x00\x00WAVEfmt "))

    def test_limiteur_debloque_apres_le_delai(self):
        t = [0.0]
        lim = serveur.LimiteurTentatives(max_echecs=3, fenetre=60, blocage=100, horloge=lambda: t[0])
        for _ in range(3):
            lim.echec("ip")
        self.assertGreater(lim.secondes_restantes("ip"), 0)
        t[0] = 101.0
        self.assertEqual(lim.secondes_restantes("ip"), 0)

    def test_limiteur_ignore_les_vieux_echecs(self):
        t = [0.0]
        lim = serveur.LimiteurTentatives(max_echecs=3, fenetre=60, blocage=100, horloge=lambda: t[0])
        lim.echec("ip")
        lim.echec("ip")
        t[0] = 120.0                                       # les deux premiers échecs sont sortis de la fenêtre
        lim.echec("ip")
        self.assertEqual(lim.secondes_restantes("ip"), 0)


if __name__ == "__main__":
    unittest.main()
