"""Lab 1 : créer un utilisateur sur une machine Linux distante via SSH.

Exemple :  python lab1_creer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta
Le mot de passe du nouveau compte est demandé en saisie masquée (jamais en argument) et doit
être changé à la première connexion.
"""

import getpass

import ssh_utils


def creer_utilisateur(argv=None) -> int:
    parser = ssh_utils.creer_parser("Crée un utilisateur sur une machine Linux distante.")
    parser.add_argument("nouvel_utilisateur", help="nom du compte à créer")
    args = parser.parse_args(argv)
    nom = ssh_utils.valider_nom_utilisateur(args.nouvel_utilisateur)

    mot_de_passe = getpass.getpass(f"Mot de passe initial de {nom} : ")
    if mot_de_passe != getpass.getpass("Confirmer : "):
        raise ValueError("Les deux mots de passe ne correspondent pas.")
    if len(mot_de_passe) < 8:
        raise ValueError("Mot de passe trop court (8 caractères minimum).")

    client = ssh_utils.connecter(args)
    try:
        cible = ssh_utils.Cible(client, args.utilisateur, args)
        print(f"[*] Création de l'utilisateur {nom}...")
        cible.lancer_ou_echouer("useradd", "-m", "--", nom)
        try:
            # le mot de passe passe par l'entrée standard de chpasswd, pas par la ligne de commande
            cible.lancer_ou_echouer("chpasswd", entree=f"{nom}:{mot_de_passe}\n")
            cible.lancer_ou_echouer("chage", "-d", "0", "--", nom)       # changement imposé à la 1re connexion
        except ssh_utils.ErreurDistante:
            cible.lancer("userdel", "-r", "--", nom)                      # ne pas laisser un compte sans mot de passe
            raise
        print(f"[+] Utilisateur {nom} créé (mot de passe à changer à la première connexion).")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(ssh_utils.main_protege(creer_utilisateur))
