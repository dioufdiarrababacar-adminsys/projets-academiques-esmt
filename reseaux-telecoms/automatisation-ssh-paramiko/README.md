# Automatisation d'administration Linux avec Paramiko

> Exposé de groupe sur l'automatisation de tâches d'administration à distance en Python avec Paramiko (SSH et SFTP), accompagné de labs sur machines virtuelles.

**Cadre :** Programmation et sécurité des réseaux (ASR soir), 2025-2026, ESMT. Travail de groupe de trois personnes.

## Contenu du rapport

- Présentation de Paramiko, installation, classes `SSHClient` et `SFTPClient`
- Labs, répartis entre les trois membres du groupe
- Bonnes pratiques de sécurité, avantages et limites

## Ma contribution

Mes trois labs : environnement Windows (poste de travail) vers une VM Kali, Python 3.13, Paramiko 3.5.1.

| Lab | Ce que fait le script | Commande exécutée à distance |
|-----|-----------------------|------------------------------|
| 1 | Création d'un utilisateur | `useradd -m` puis `chpasswd` |
| 1.5 | Suppression d'un utilisateur | `sudo -S userdel -r` |
| 2 | Redémarrage ou arrêt de la machine | `sudo -S reboot` ou `shutdown` |

Les autres labs du rapport (mise à jour `apt` à distance, transfert SFTP, connexion et exécution de commandes, installation d'un paquet) ont été réalisés par mes deux coéquipières.

## Portée

Chaque lab cible une seule machine virtuelle. Il s'agit d'une démonstration des primitives Paramiko, pas d'une automatisation de parc ni d'équipements réseau.

## Limites connues

Les scripts du rapport enfreignent plusieurs des bonnes pratiques que le rapport recommande lui-même :

- Identifiants en clair dans le code, et connexion en `root` par mot de passe pour le lab 1 (le rapport conseille clés SSH et `PermitRootLogin no`).
- `AutoAddPolicy` accepte n'importe quelle clé d'hôte, ce qui expose à une attaque de l'homme du milieu. À remplacer par la vérification de `known_hosts`.
- `echo mot_de_passe | sudo -S` place le mot de passe dans la ligne de commande, visible dans la liste des processus. Il vaut mieux l'envoyer sur l'entrée standard de la commande ou configurer `sudo` sans mot de passe pour la tâche précise.
- Avec `get_pty=True`, la sortie d'erreur est fusionnée dans la sortie standard : le test `if error:` ne détecte plus rien, et le mot de passe est renvoyé en écho dans la sortie du lab 1.5.

## Fichiers

Les scripts ne sont pas encore dans ce dépôt, ils n'existent que sous forme de captures dans le rapport. Le rapport complet n'est pas publié, car il contient des captures de mes coéquipières.
