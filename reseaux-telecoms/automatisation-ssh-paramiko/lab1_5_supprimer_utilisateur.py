"""Lab 1.5 (bonus) : supprimer un utilisateur sur une machine Linux distante via SSH.

Exemple :  python lab1_5_supprimer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta

Garde-fous absents du script d'origine : le compte doit exister, avoir un UID d'utilisateur
ordinaire (>= 1000, donc ni root ni un compte système) et ne pas être celui de la connexion SSH.
"""

import ssh_utils

UID_MIN_UTILISATEUR = 1000


def supprimer_utilisateur(argv=None) -> int:
    parser = ssh_utils.creer_parser("Supprime un utilisateur (et son dossier personnel) sur une machine Linux distante.")
    parser.add_argument("utilisateur_a_supprimer", help="nom du compte à supprimer")
    args = parser.parse_args(argv)
    nom = ssh_utils.valider_nom_utilisateur(args.utilisateur_a_supprimer)

    client = ssh_utils.connecter(args)
    try:
        cible = ssh_utils.Cible(client, args.utilisateur, args)
        if nom == args.utilisateur:
            raise ValueError("Refus : ce compte est celui de la connexion SSH.")

        code, sortie, _ = cible.lancer("id", "-u", "--", nom, sudo=False)
        if code != 0:
            raise ValueError(f"L'utilisateur {nom} n'existe pas sur la cible.")
        if not sortie.strip().isdigit() or int(sortie) < UID_MIN_UTILISATEUR:
            raise ValueError(f"Refus : {nom} (UID {sortie.strip()}) est un compte système.")

        if not ssh_utils.confirmer(f"Supprimer {nom} et son dossier personnel sur {args.hote} ?", args):
            print("[*] Annulé.")
            return 1

        cible.lancer_ou_echouer("userdel", "-r", "--", nom)
        print(f"[+] Utilisateur {nom} supprimé.")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(ssh_utils.main_protege(supprimer_utilisateur))
