#!/usr/bin/env bash
# Test de fumée du point d'entrée de vote : vérifie les refus et le comportement attendu.
#
# Prérequis : le site tourne (ex. php -S 127.0.0.1:8081 -t src), VOTE_CONFIG pointe vers un config.ini
# valide, et la table `votes` est VIDE (TRUNCATE votes) car le test y insère deux votes.
#
#   BASE=http://127.0.0.1:8081 TOKEN=<token du config.ini> ./test-vote.sh
set -u
BASE="${BASE:-http://127.0.0.1:8081}"
TOKEN="${TOKEN:?définir TOKEN (valeur de « token » dans config.ini)}"
echec=0

attendre() {   # attendre <code http attendu> <description> <arguments curl...>
  local attendu="$1" libelle="$2"; shift 2
  local obtenu
  obtenu=$(curl -s -o /dev/null -w "%{http_code}" "$@")
  if [ "$obtenu" = "$attendu" ]; then echo "ok   $libelle"; else echo "ECHEC $libelle (attendu $attendu, obtenu $obtenu)"; echec=1; fi
}

U="$BASE/enregistrervote.php"; H="X-Vote-Token: $TOKEN"
attendre 405 "GET refusé"                          "$U?touche=1&votant=1"
attendre 403 "POST sans jeton refusé"              -X POST -d "touche=1&votant=221770000001" "$U"
attendre 403 "POST avec mauvais jeton refusé"      -X POST -H "X-Vote-Token: faux" -d "touche=1&votant=221770000001" "$U"
attendre 200 "vote valide, touche 1"               -X POST -H "$H" -d "touche=1&votant=221770000001" "$U"
attendre 409 "second vote du même numéro refusé"   -X POST -H "$H" -d "touche=2&votant=221770000001" "$U"
attendre 200 "vote valide, touche 2"               -X POST -H "$H" -d "touche=2&votant=221770000002" "$U"
attendre 400 "touche inconnue refusée"             -X POST -H "$H" -d "touche=3&votant=221770000003" "$U"
attendre 400 "injection SQL dans le numéro refusée"   -X POST -H "$H" --data-urlencode "touche=1" --data-urlencode "votant=1' OR '1'='1" "$U"
attendre 400 "injection shell dans le numéro refusée" -X POST -H "$H" --data-urlencode "touche=1" --data-urlencode 'votant=1";id;"' "$U"
attendre 200 "page de résultats accessible"        "$BASE/resultats.php"

exit $echec
