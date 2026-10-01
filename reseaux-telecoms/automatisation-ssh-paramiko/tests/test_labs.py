"""Tests des labs Paramiko contre une machine Linux fictive pilotée par un vrai serveur SSH (Paramiko).

Lancer depuis le dossier du projet :  python -m unittest discover -s tests -v
La machine fictive enregistre chaque ligne de commande reçue : les tests vérifient qu'aucun mot de
passe n'y apparaît, que la clé d'hôte est vérifiée et que les erreurs distantes sont bien remontées.
"""

import contextlib
import io
import os
import shlex
import socket
import sys
import tempfile
import threading
import unittest
from unittest import mock

import paramiko

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lab1_5_supprimer_utilisateur as lab15   # noqa: E402
import lab1_creer_utilisateur as lab1           # noqa: E402
import lab2_redemarrage as lab2                 # noqa: E402
import ssh_utils                                # noqa: E402

MDP_SSH, MDP_SUDO, MDP_NOUVEAU = "ssh-secret-xyz", "sudo-secret-xyz", "Nouveau-mdp-123"


class MachineFictive(paramiko.ServerInterface):
    """Mini machine Linux : comptes, sudo, useradd/chpasswd/chage/userdel/id/shutdown."""

    def __init__(self):
        self.utilisateurs = {"root": 0, "kali": 1000, "alice": 1001, "busy": 1002}
        self.mots_de_passe = {}
        self.chage = []
        self.commandes = []        # lignes de commande brutes reçues par le serveur SSH
        self.arrets = []
        self.echec_chpasswd = False

    # -- authentification SSH --
    def check_auth_password(self, utilisateur, mot_de_passe):
        ok = utilisateur == "kali" and mot_de_passe == MDP_SSH
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def get_allowed_auths(self, utilisateur):
        return "password"

    def check_channel_request(self, genre, id_canal):
        return paramiko.OPEN_SUCCEEDED if genre == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, canal, commande):
        threading.Thread(target=self._traiter, args=(canal, commande.decode()), daemon=True).start()
        return True

    # -- exécution --
    def _traiter(self, canal, commande):
        self.commandes.append(commande)
        entree = b""
        while True:                                   # lit jusqu'à l'EOF envoyé par shutdown_write()
            morceau = canal.recv(4096)
            if not morceau:
                break
            entree += morceau
        sortie, erreur, code = self._executer(commande, entree.decode())
        if sortie:
            canal.sendall(sortie.encode())
        if erreur:
            canal.sendall_stderr(erreur.encode())
        canal.send_exit_status(code)
        canal.close()

    def _executer(self, commande, entree):
        argv, lignes = shlex.split(commande), entree.split("\n")
        if argv[0] == "sudo":
            if argv[1] == "-S":
                argv, mdp, reste = argv[4:], lignes[0], "\n".join(lignes[1:])
                if mdp != MDP_SUDO:
                    return "", "Sorry, try again.\n", 1
            else:                                     # sudo -n
                argv, reste = argv[2:], entree
        else:
            reste = entree
        nom_cmd, args = argv[0], argv[1:]
        if nom_cmd == "id":
            nom = args[-1]
            return (f"{self.utilisateurs[nom]}\n", "", 0) if nom in self.utilisateurs else ("", f"id: '{nom}': no such user\n", 1)
        if nom_cmd == "useradd":
            nom = args[-1]
            if nom in self.utilisateurs:
                return "", f"useradd: user '{nom}' already exists\n", 9
            self.utilisateurs[nom] = 2000 + len(self.utilisateurs)
            return "", "", 0
        if nom_cmd == "chpasswd":
            if self.echec_chpasswd:
                return "", "chpasswd: (line 1, user x) password not changed\n", 1
            nom, mdp = reste.strip().split(":", 1)
            self.mots_de_passe[nom] = mdp
            return "", "", 0
        if nom_cmd == "chage":
            self.chage.append(args)
            return "", "", 0
        if nom_cmd == "userdel":
            nom = args[-1]
            if nom == "busy":
                return "", "userdel: user busy is currently used by process 1\n", 8
            self.utilisateurs.pop(nom, None)
            return "", "userdel: alice mail spool (/var/mail/alice) not found\n", 0   # avertissement bénin
        if nom_cmd == "shutdown":
            self.arrets.append(args)
            return "", "", 0
        return "", f"{nom_cmd}: command not found\n", 127


class TestLabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cle_hote = paramiko.RSAKey.generate(2048)
        cls.ecoute = socket.socket()
        cls.ecoute.bind(("127.0.0.1", 0))
        cls.ecoute.listen(5)
        cls.ecoute.settimeout(0.5)
        cls.port = cls.ecoute.getsockname()[1]
        cls.arret = threading.Event()
        cls.machine = None
        cls.transports = []
        cls.fil = threading.Thread(target=cls._accepter, daemon=True)
        cls.fil.start()
        cls.dossier = tempfile.mkdtemp()
        cls.known_hosts = os.path.join(cls.dossier, "known_hosts")
        with open(cls.known_hosts, "w") as f:
            f.write(f"[127.0.0.1]:{cls.port} {cls.cle_hote.get_name()} {cls.cle_hote.get_base64()}\n")
        cls.known_hosts_vide = os.path.join(cls.dossier, "vide")
        open(cls.known_hosts_vide, "w").close()

    @classmethod
    def _accepter(cls):
        while not cls.arret.is_set():
            try:
                conn, _ = cls.ecoute.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            t = paramiko.Transport(conn)
            t.add_server_key(cls.cle_hote)
            cls.transports.append(t)
            try:
                t.start_server(server=cls.machine)
            except paramiko.SSHException:
                continue

    @classmethod
    def tearDownClass(cls):
        cls.arret.set()
        cls.ecoute.close()
        for t in cls.transports:
            t.close()

    def setUp(self):
        type(self).machine = MachineFictive()

    # -- outils --
    def lancer(self, module_fonction, args, ssh_hosts=None, entrees=None, saisies_perso=None):
        """Exécute un lab avec des saisies simulées. Retourne (code de sortie, sortie standard, erreur standard)."""
        saisies = {"ssh": MDP_SSH, "sudo": MDP_SUDO, "initial": MDP_NOUVEAU, "confirmer": MDP_NOUVEAU}
        saisies.update(saisies_perso or {})

        def faux_getpass(invite=""):
            texte = invite.lower()
            for mot, valeur in saisies.items():
                if mot in texte:
                    return valeur
            raise AssertionError(f"invite inattendue : {invite!r}")

        argv = ["127.0.0.1", "-p", str(self.port), "-u", "kali", "--known-hosts", ssh_hosts or self.known_hosts] + args
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("getpass.getpass", faux_getpass), \
             mock.patch("builtins.input", lambda *_: (entrees or ["n"]).pop(0)), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ssh_utils.main_protege(lambda _: module_fonction(argv))
        return code, out.getvalue(), err.getvalue()

    def assertAucun_secret_dans_les_commandes(self):
        for c in self.machine.commandes:
            for secret in (MDP_SSH, MDP_SUDO, MDP_NOUVEAU):
                self.assertNotIn(secret, c, f"secret visible dans la ligne de commande : {c}")

    # -- lab 1 : créer un utilisateur --
    def test_lab1_cree_utilisateur_sans_secret_en_ligne_de_commande(self):
        code, sortie, _ = self.lancer(lab1.creer_utilisateur, ["fanta"])
        self.assertEqual(code, 0, sortie)
        self.assertIn("fanta", self.machine.utilisateurs)
        self.assertEqual(self.machine.mots_de_passe["fanta"], MDP_NOUVEAU)
        self.assertEqual(self.machine.chage, [["-d", "0", "--", "fanta"]])
        self.assertAucun_secret_dans_les_commandes()

    def test_lab1_mauvais_mot_de_passe_sudo(self):
        code, _, err = self.lancer(lab1.creer_utilisateur, ["fanta"], saisies_perso={"sudo": "mauvais-sudo"})
        self.assertEqual(code, 1)
        self.assertIn("Sorry, try again", err)
        self.assertNotIn("fanta", self.machine.utilisateurs)

    def test_lab1_annule_la_creation_si_chpasswd_echoue(self):
        self.machine.echec_chpasswd = True
        code, _, err = self.lancer(lab1.creer_utilisateur, ["fanta"])
        self.assertEqual(code, 1)
        self.assertIn("chpasswd a échoué", err)
        self.assertNotIn("fanta", self.machine.utilisateurs)      # pas de compte orphelin sans mot de passe

    def test_lab1_nom_invalide_aucune_connexion(self):
        for nom in ("fanta; rm -rf /", "Root", "a b", "$(id)", "", "x" * 40, "-oProxy"):
            self.machine.commandes.clear()
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    code = self.lancer(lab1.creer_utilisateur, [nom])[0]
            except SystemExit as e:              # argparse refuse lui-même un nom vide ou qui ressemble à une option
                code = e.code
            self.assertNotEqual(code, 0, nom)
            self.assertEqual(self.machine.commandes, [], f"{nom!r} a atteint la machine")

    def test_lab1_utilisateur_deja_existant(self):
        code, _, err = self.lancer(lab1.creer_utilisateur, ["alice"])
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    # -- sécurité de la connexion --
    def test_cle_d_hote_inconnue_refusee(self):
        code, _, err = self.lancer(lab1.creer_utilisateur, ["fanta"], ssh_hosts=self.known_hosts_vide)
        self.assertEqual(code, 1)
        self.assertEqual(self.machine.commandes, [])
        self.assertIn("known_hosts", err)

    def test_authentification_refusee(self):
        code, _, err = self.lancer(lab2.redemarrer, ["--oui", "reboot"], saisies_perso={"ssh": "mauvais-ssh"})
        self.assertEqual(code, 1)
        self.assertIn("Authentification refusée", err)
        self.assertEqual(self.machine.arrets, [])

    # -- lab 1.5 : supprimer un utilisateur --
    def test_lab15_supprime_un_utilisateur_ordinaire(self):
        code, sortie, err = self.lancer(lab15.supprimer_utilisateur, ["--oui", "alice"])
        self.assertEqual(code, 0, err)
        self.assertNotIn("alice", self.machine.utilisateurs)
        self.assertAucun_secret_dans_les_commandes()

    def test_lab15_avertissement_bénin_ne_fait_pas_echouer(self):
        # userdel émet « mail spool not found » sur stderr mais réussit (code 0) : c'est un succès
        code, _, _ = self.lancer(lab15.supprimer_utilisateur, ["--oui", "alice"])
        self.assertEqual(code, 0)

    def test_lab15_refuse_root_soi_meme_et_inexistant(self):
        for nom, motif in (("root", "compte système"), ("kali", "connexion SSH"), ("fantome", "n'existe pas")):
            code, _, err = self.lancer(lab15.supprimer_utilisateur, ["--oui", nom])
            self.assertEqual(code, 1, nom)
            self.assertIn(motif, err)
        self.assertIn("root", self.machine.utilisateurs)

    def test_lab15_vraie_erreur_remontee(self):
        code, _, err = self.lancer(lab15.supprimer_utilisateur, ["--oui", "busy"])
        self.assertEqual(code, 1)
        self.assertIn("currently used by process", err)           # l'ancien script affichait « succès »
        self.assertIn("busy", self.machine.utilisateurs)

    def test_lab15_confirmation_refusee(self):
        code, _, _ = self.lancer(lab15.supprimer_utilisateur, ["alice"], entrees=["n"])
        self.assertEqual(code, 1)
        self.assertIn("alice", self.machine.utilisateurs)

    # -- lab 2 : redémarrage --
    def test_lab2_reboot_et_shutdown_avec_delai(self):
        self.assertEqual(self.lancer(lab2.redemarrer, ["--oui", "reboot"])[0], 0)
        self.assertEqual(self.lancer(lab2.redemarrer, ["--oui", "shutdown", "--delai", "5"])[0], 0)
        self.assertEqual(self.machine.arrets, [["-r", "now"], ["-h", "+5"]])
        self.assertAucun_secret_dans_les_commandes()

    def test_lab2_delai_hors_limites_et_action_inconnue(self):
        self.assertEqual(self.lancer(lab2.redemarrer, ["--oui", "reboot", "--delai", "99999"])[0], 1)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.lancer(lab2.redemarrer, ["--oui", "format-c"])
        self.assertEqual(self.machine.arrets, [])

    def test_lab2_confirmation_refusee(self):
        self.assertEqual(self.lancer(lab2.redemarrer, ["reboot"], entrees=["non"])[0], 1)
        self.assertEqual(self.machine.arrets, [])


if __name__ == "__main__":
    unittest.main()
