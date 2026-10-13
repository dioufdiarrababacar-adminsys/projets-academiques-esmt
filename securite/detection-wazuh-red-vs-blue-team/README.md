# Détection d'intrusion avec Wazuh : Red Team vs Blue Team

> Simulation d'attaques contre un environnement surveillé par Wazuh 4.14, avec analyse des alertes et mesure des temps de détection.

**Cadre :** Administration Linux et programmation Shell, Master 1 SSI-ISI, ESMT, septembre 2026. Projet de groupe.
**Ma contribution :** _à compléter_

## Architecture

Trois machines virtuelles : un serveur Wazuh en mode All-in-One (manager, indexer, dashboard), une machine cible Debian avec un agent Wazuh, et une machine attaquante (Ubuntu ou Kali selon le scénario).

## Réalisé

- Installation automatisée du serveur par script Bash (Wazuh 4.14, Postfix en relais SMTP pour les alertes par email)
- Enregistrement de l'agent et collecte des journaux SSH, Apache et système
- Règles personnalisées (brute force, attaques web, malware, mouvement latéral) et alertes par email

## Scénarios

| Scénario | Outil | Détection observée | Délai |
|----------|-------|--------------------|-------|
| Brute force SSH | Hydra | règles 5760 puis 5763 | ≈ 4 s |
| Injection SQL et XSS sur DVWA | navigateur | règles 31101 et 31106 | ≈ 1 s |
| Malware simulé (fichier EICAR) | scp | règle 87105 (VirusTotal) | ≤ 15 s |
| Mouvement latéral par pivot SSH | Hydra | règle 5760, rattachée à MITRE ATT&CK (T1110.001, T1021.004) | ≈ 10 s |

## Limites

- Les alertes observées viennent de règles natives de Wazuh : les règles personnalisées 100001 à 100009 n'ont pas été validées par ces tests
- Aucune réponse active configurée, donc pas de temps de réponse mesuré
- Les scénarios ont été joués sur deux plates-formes de test différentes

## Suite prévue

Valider chaque règle personnalisée avec `wazuh-logtest`, configurer une réponse active (`firewall-drop`) et rejouer l'ensemble sur une plate-forme unique.

Le rapport complet est disponible sur demande.
