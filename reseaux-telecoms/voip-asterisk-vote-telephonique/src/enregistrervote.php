<?php
declare(strict_types=1);

/*
 * Enregistre un vote reçu d'Asterisk.
 *
 * Appelé uniquement par le dialplan, en POST, depuis la machine elle-même, avec un secret partagé.
 * Version corrigée après revue de sécurité. Par rapport à la version rendue :
 *   - plus d'accès public : refus hors localhost, refus sans jeton, refus des requêtes GET
 *   - la touche est validée et traduite en nom de candidat côté serveur (le client ne choisit plus le texte)
 *   - requêtes préparées (PDO), identifiants lus hors du dossier web, erreurs jamais affichées
 *   - un seul vote par numéro d'appelant (contrainte UNIQUE en base)
 */

const CANDIDATS = ['1' => 'Modou Lô', '2' => 'Balla Gaye'];

header('Content-Type: text/plain; charset=utf-8');
ini_set('display_errors', '0');          // les erreurs vont dans le journal du serveur, pas vers l'appelant
error_reporting(E_ALL);

function repondre(int $code, string $message): never
{
    http_response_code($code);
    exit($message . "\n");
}

$config = @parse_ini_file(getenv('VOTE_CONFIG') ?: '/etc/asterisk-vote/config.ini');
if ($config === false || empty($config['token']) || empty($config['dsn'])) {
    error_log('enregistrervote.php : configuration illisible ou incomplète');
    repondre(500, 'Erreur serveur');
}

if (!in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1', '::1'], true)) {
    repondre(403, 'Interdit');
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    repondre(405, 'Méthode non autorisée');
}
if (!hash_equals((string) $config['token'], (string) ($_SERVER['HTTP_X_VOTE_TOKEN'] ?? ''))) {
    repondre(403, 'Interdit');
}

$touche = $_POST['touche'] ?? '';
$votant = $_POST['votant'] ?? '';
if (!is_string($touche) || !isset(CANDIDATS[$touche])) {
    repondre(400, 'Choix invalide');
}
if (!is_string($votant) || !preg_match('/^[0-9]{1,20}$/', $votant)) {
    repondre(400, 'Numéro invalide');
}

try {
    $pdo = new PDO($config['dsn'], $config['utilisateur'] ?? null, $config['mot_de_passe'] ?? null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $requete = $pdo->prepare('INSERT INTO votes (votant, candidat) VALUES (:votant, :candidat)');
    $requete->execute([':votant' => $votant, ':candidat' => CANDIDATS[$touche]]);
} catch (PDOException $e) {
    if ($e->getCode() === '23000') {      // violation de la contrainte UNIQUE sur votant
        repondre(409, 'Déjà voté');
    }
    error_log('enregistrervote.php : ' . $e->getMessage());
    repondre(500, 'Erreur serveur');
}

repondre(200, 'Vote enregistré');
