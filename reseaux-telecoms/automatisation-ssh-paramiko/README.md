# Automatisation d'administration Linux avec Paramiko

> Exposé de groupe sur l'automatisation de tâches d'administration à distance en Python avec Paramiko (SSH et SFTP), accompagné de labs sur machines virtuelles.

**Cadre :** Programmation et sécurité des réseaux (ASR soir), 2025-2026, ESMT. Travail de groupe de trois personnes.

## Ma contribution

Trois labs, d'un poste Windows vers une VM Kali (Python 3.13, Paramiko 3.5.1) :

| Lab | Script | Ce que fait le script |
|-----|--------|-----------------------|
| 1 | [`lab1_creer_utilisateur.py`](lab1_creer_utilisateur.py) | Crée un utilisateur et lui impose de changer son mot de passe à la première connexion |
| 1.5 | [`lab1_5_supprimer_utilisateur.py`](lab1_5_supprimer_utilisateur.py) | Supprime un utilisateur et son dossier personnel |
| 2 | [`lab2_redemarrage.py`](lab2_redemarrage.py) | Redémarre ou éteint la machine, immédiatement ou avec un délai |

Chaque lab cible une seule machine : c'est une démonstration des primitives Paramiko, pas une automatisation de parc ni d'équipements réseau.

## Sécurité

- Clé d'hôte vérifiée (`known_hosts`), authentification par clé SSH ou mot de passe saisi en masqué
- Aucun mot de passe dans le code ni dans les lignes de commande
- Succès jugé sur le code de sortie de la commande distante
- Noms d'utilisateur validés, refus de supprimer `root` ou un compte système

## Utilisation

```bash
pip install -r requirements.txt

# La clé d'hôte doit être connue : vérifier son empreinte, puis l'ajouter
ssh-keyscan -H 192.168.15.150 >> ~/.ssh/known_hosts

python lab1_creer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta
python lab1_5_supprimer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta
python lab2_redemarrage.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 reboot --delai 5
```

Sans `-i`, le mot de passe SSH est demandé. `--sudo-nopasswd` s'utilise si `sudo` est configuré sans mot de passe sur la cible, `--oui` supprime les confirmations.

## Tests

```bash
python -m unittest discover -s tests -v
```
