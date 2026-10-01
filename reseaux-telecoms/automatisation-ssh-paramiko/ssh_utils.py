"""Fonctions communes aux labs Paramiko : connexion SSH sûre et exécution de commandes.

Par rapport aux scripts d'origine :
  - la clé d'hôte est vérifiée (known_hosts + RejectPolicy) au lieu de AutoAddPolicy
  - authentification par clé SSH, ou mot de passe saisi avec getpass : plus rien en dur dans le code
  - le mot de passe sudo passe par l'entrée standard de la commande, jamais dans la ligne de commande
  - pas de pseudo-terminal : la sortie d'erreur reste séparée (donc exploitable) et rien n'est renvoyé en écho
  - le succès est jugé sur le code de sortie de la commande, pas sur le contenu de stderr
  - les arguments sont protégés par shlex.quote et les noms d'utilisateur validés
"""

import argparse
import getpass
import re
import shlex
import sys
import threading

import paramiko

RE_NOM_UTILISATEUR = re.compile(r"[a-z_][a-z0-9_-]{0,31}")


class ErreurDistante(Exception):
    """Une commande distante a échoué (code de sortie non nul)."""


def valider_nom_utilisateur(nom: str) -> str:
    if not RE_NOM_UTILISATEUR.fullmatch(nom or ""):
        raise ValueError(f"Nom d'utilisateur invalide : {nom!r} "
                         "(minuscules, chiffres, '_' et '-', 32 caractères maximum, pas de chiffre en tête).")
    return nom


def creer_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("hote", help="adresse IP ou nom de la machine cible")
    p.add_argument("-p", "--port", type=int, default=22)
    p.add_argument("-u", "--utilisateur", required=True, help="compte SSH utilisé pour se connecter")
    p.add_argument("-i", "--cle", help="clé privée SSH (recommandé) ; sinon le mot de passe est demandé")
    p.add_argument("--known-hosts", help="fichier known_hosts supplémentaire (par défaut ~/.ssh/known_hosts)")
    p.add_argument("--sudo-nopasswd", action="store_true",
                   help="sudo ne demande pas de mot de passe sur la cible (règle NOPASSWD)")
    p.add_argument("--oui", action="store_true", help="ne pas demander de confirmation")
    return p


def connecter(args) -> paramiko.SSHClient:
    """Ouvre la connexion SSH en refusant toute machine dont la clé n'est pas déjà connue."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if args.known_hosts:
        client.load_host_keys(args.known_hosts)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    mot_de_passe = None if args.cle else getpass.getpass(f"Mot de passe SSH de {args.utilisateur}@{args.hote} : ")
    client.connect(args.hote, port=args.port, username=args.utilisateur, password=mot_de_passe,
                   key_filename=args.cle, timeout=10, allow_agent=False, look_for_keys=False)
    return client


def executer(client, commande: str, entree: str = "", timeout: int = 60):
    """Exécute une commande sans pty. Retourne (code_de_sortie, stdout, stderr)."""
    stdin, stdout, stderr = client.exec_command(commande, timeout=timeout)
    if entree:
        stdin.write(entree)
        stdin.flush()
    stdin.channel.shutdown_write()

    morceaux = {}

    def lire(nom, flux):
        morceaux[nom] = flux.read().decode("utf-8", errors="replace")

    lecteur = threading.Thread(target=lire, args=("err", stderr))
    lecteur.start()                     # stderr lu en parallèle : évite l'interblocage si les deux se remplissent
    lire("out", stdout)
    lecteur.join()
    return stdout.channel.recv_exit_status(), morceaux["out"], morceaux["err"]


class Cible:
    """Machine distante : exécute des commandes, avec sudo quand le compte n'est pas root."""

    def __init__(self, client, utilisateur: str, args):
        self.client = client
        self.root = utilisateur == "root"
        self.nopasswd = args.sudo_nopasswd
        self._mdp_sudo = None

    def _mot_de_passe_sudo(self) -> str:
        if self._mdp_sudo is None:
            self._mdp_sudo = getpass.getpass("Mot de passe sudo sur la cible : ")
        return self._mdp_sudo

    def lancer(self, *argv: str, entree: str = "", sudo: bool = True):
        """Lance argv (liste d'arguments, jamais une chaîne assemblée à la main). Retourne (code, out, err)."""
        commande = " ".join(shlex.quote(a) for a in argv)
        if not sudo or self.root:
            return executer(self.client, commande, entree)
        if self.nopasswd:
            return executer(self.client, "sudo -n " + commande, entree)
        # sudo lit le mot de passe sur la première ligne de stdin ; la commande lit le reste.
        return executer(self.client, "sudo -S -p '' " + commande, self._mot_de_passe_sudo() + "\n" + entree)

    def lancer_ou_echouer(self, *argv: str, entree: str = "", sudo: bool = True) -> str:
        code, sortie, erreur = self.lancer(*argv, entree=entree, sudo=sudo)
        if code != 0:
            raise ErreurDistante(f"{argv[0]} a échoué (code {code}) : {erreur.strip() or sortie.strip() or 'aucun détail'}")
        return sortie


def confirmer(question: str, args) -> bool:
    if args.oui:
        return True
    return input(f"{question} [o/N] ").strip().lower() in ("o", "oui", "y", "yes")


def main_protege(fonction, argv=None) -> int:
    """Exécute fonction(args) avec une gestion d'erreurs lisible ; retourne le code de sortie du programme."""
    try:
        return fonction(argv) or 0
    except paramiko.ssh_exception.AuthenticationException:
        print("[-] Authentification refusée (identifiant, mot de passe ou clé incorrects).", file=sys.stderr)
    except paramiko.ssh_exception.SSHException as e:
        print(f"[-] Connexion SSH refusée : {e}\n    Si la clé d'hôte est inconnue, vérifiez d'abord son empreinte "
              f"puis ajoutez-la : ssh-keyscan -H <hote> >> ~/.ssh/known_hosts", file=sys.stderr)
    except (ErreurDistante, ValueError, OSError) as e:
        print(f"[-] {e}", file=sys.stderr)
    return 1
