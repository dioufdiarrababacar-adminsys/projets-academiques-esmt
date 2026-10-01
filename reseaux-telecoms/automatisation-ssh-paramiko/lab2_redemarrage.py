"""Lab 2 : redémarrer ou éteindre une machine Linux distante via SSH.

Exemples :
  python lab2_redemarrage.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 reboot
  python lab2_redemarrage.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 shutdown --delai 5
"""

import ssh_utils

OPTION_SHUTDOWN = {"reboot": "-r", "shutdown": "-h"}


def redemarrer(argv=None) -> int:
    parser = ssh_utils.creer_parser("Redémarre ou éteint une machine Linux distante.")
    parser.add_argument("action", choices=sorted(OPTION_SHUTDOWN))
    parser.add_argument("--delai", type=int, default=0, help="délai en minutes avant l'action (0 = immédiat)")
    args = parser.parse_args(argv)
    if not 0 <= args.delai <= 1440:
        raise ValueError("Le délai doit être compris entre 0 et 1440 minutes.")

    if not ssh_utils.confirmer(f"Faire un '{args.action}' sur {args.hote} ?", args):
        print("[*] Annulé.")
        return 1

    client = ssh_utils.connecter(args)
    try:
        cible = ssh_utils.Cible(client, args.utilisateur, args)
        quand = "now" if args.delai == 0 else f"+{args.delai}"
        code, sortie, erreur = cible.lancer("shutdown", OPTION_SHUTDOWN[args.action], quand)
        # -1 : la machine a coupé la connexion avant d'envoyer le code de sortie, ce qui est normal ici
        if code not in (0, -1):
            raise ssh_utils.ErreurDistante(f"shutdown a échoué (code {code}) : {erreur.strip() or sortie.strip()}")
        print(f"[+] Commande acceptée : {args.action} prévu ({'immédiat' if args.delai == 0 else f'dans {args.delai} min'}).")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(ssh_utils.main_protege(redemarrer))
