# Automatisation d'administration Linux avec Paramiko

> Exposé de groupe sur l'automatisation de tâches d'administration à distance en Python avec Paramiko (SSH et SFTP), accompagné de labs sur machines virtuelles. Les trois scripts de ma partie sont ici en version corrigée après revue de sécurité.

**Cadre :** Programmation et sécurité des réseaux (ASR soir), 2025-2026, ESMT. Travail de groupe de trois personnes.

## Contenu du rapport

- Présentation de Paramiko, installation, classes `SSHClient` et `SFTPClient`
- Labs, répartis entre les trois membres du groupe
- Bonnes pratiques de sécurité, avantages et limites

Le rapport complet n'est pas publié, car il contient des captures de mes coéquipières.

## Ma contribution

Mes trois labs : poste Windows vers une VM Kali, Python 3.13, Paramiko 3.5.1. Les scripts d'origine n'existent que sous forme de captures dans le rapport. Ce dépôt contient leur version corrigée.

| Lab | Script | Ce que fait le script |
|-----|--------|-----------------------|
| 1 | [`lab1_creer_utilisateur.py`](lab1_creer_utilisateur.py) | Crée un utilisateur et lui impose de changer son mot de passe à la première connexion |
| 1.5 | [`lab1_5_supprimer_utilisateur.py`](lab1_5_supprimer_utilisateur.py) | Supprime un utilisateur et son dossier personnel, avec garde-fous |
| 2 | [`lab2_redemarrage.py`](lab2_redemarrage.py) | Redémarre ou éteint la machine, immédiatement ou avec un délai |

Les autres labs du rapport (mise à jour `apt` à distance, transfert SFTP, connexion et exécution de commandes, installation d'un paquet) ont été réalisés par mes deux coéquipières.

Chaque lab cible une seule machine : c'est une démonstration des primitives Paramiko, pas une automatisation de parc ni d'équipements réseau.

## Revue de sécurité : ce qui a changé

Les scripts d'origine enfreignaient plusieurs des bonnes pratiques que le rapport recommande lui-même.

| Script d'origine | Correction |
|------------------|-----------|
| Identifiants en clair dans le code | Clé SSH (`-i`) ou mot de passe saisi en masqué avec `getpass` ; plus aucun secret dans le code ni dans les arguments |
| `AutoAddPolicy` : n'importe quelle clé d'hôte est acceptée (homme du milieu) | `known_hosts` et `RejectPolicy` : une machine inconnue est refusée |
| Connexion en `root` par mot de passe | Compte ordinaire, `sudo` quand c'est nécessaire |
| `echo mot_de_passe \| sudo -S ...` : mot de passe visible dans la liste des processus | Mot de passe sudo envoyé sur l'entrée standard de la commande |
| `useradd ... && echo 'user:mdp' \| chpasswd` : mot de passe du nouveau compte dans la ligne de commande | `chpasswd` lit `user:mot_de_passe` sur son entrée standard |
| `get_pty=True` : stderr fusionné dans stdout (le test `if error:` ne détecte plus rien) et mot de passe renvoyé en écho dans la sortie | Pas de pseudo-terminal, stdout et stderr séparés, succès jugé sur le code de sortie |
| Commande construite par concaténation de chaînes (injection possible) | Arguments protégés par `shlex.quote`, noms d'utilisateur validés par expression régulière |
| Suppression de n'importe quel compte, y compris `root` | Le compte doit exister, avoir un UID d'au moins 1000 et ne pas être celui de la connexion ; confirmation demandée |
| Compte créé sans mot de passe si `chpasswd` échoue | Annulation automatique de la création |

## Utilisation

```bash
pip install -r requirements.txt

# La clé d'hôte doit être connue : vérifier son empreinte, puis l'ajouter
ssh-keyscan -H 192.168.15.150 >> ~/.ssh/known_hosts

python lab1_creer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta
python lab1_5_supprimer_utilisateur.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 fanta
python lab2_redemarrage.py 192.168.15.150 -u kali -i ~/.ssh/id_ed25519 reboot --delai 5
```

Sans `-i`, le mot de passe SSH est demandé. `--sudo-nopasswd` s'utilise si `sudo` est configuré sans mot de passe sur la cible. `--oui` supprime les demandes de confirmation.

## Tests

```bash
python -m unittest discover -s tests -v
```

15 tests contre une machine Linux fictive pilotée par un vrai serveur SSH Paramiko. Elle enregistre chaque ligne de commande reçue : les tests vérifient qu'aucun mot de passe n'y apparaît, qu'une clé d'hôte inconnue est refusée, qu'un mot de passe sudo ou SSH erroné échoue proprement, que les noms d'utilisateur dangereux n'atteignent jamais la machine, qu'une vraie erreur de `userdel` est remontée (et qu'un simple avertissement ne fait pas échouer), et que la création est annulée si `chpasswd` échoue.

Ces tests n'ont pas été joués contre une vraie machine Linux : le comportement réel de `sudo -S` avec une entrée standard partagée avec la commande reste à confirmer sur une VM.

## Limites restantes

- Les labs restent mono-machine. Pour un parc, utiliser un outil d'orchestration (Ansible) plutôt que des scripts Paramiko.
- L'authentification par clé suppose une clé sans phrase de passe, ou un agent SSH (désactivé dans ces scripts).
