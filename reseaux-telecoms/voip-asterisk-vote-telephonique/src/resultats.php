<?php
declare(strict_types=1);

/*
 * Page publique des résultats : lecture seule, aucun paramètre accepté.
 * Version corrigée : requête PDO, sortie échappée, pas de division par zéro,
 * erreurs jamais affichées, Chart.js figé en version et vérifié par SRI.
 */

ini_set('display_errors', '0');
error_reporting(E_ALL);

$config = @parse_ini_file(getenv('VOTE_CONFIG') ?: '/etc/asterisk-vote/config.ini');
try {
    if ($config === false || empty($config['dsn'])) {
        throw new RuntimeException('configuration illisible');
    }
    $pdo = new PDO($config['dsn'], $config['utilisateur'] ?? null, $config['mot_de_passe'] ?? null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    ]);
    $lignes = $pdo->query('SELECT candidat, COUNT(*) AS total FROM votes GROUP BY candidat ORDER BY total DESC')
                  ->fetchAll(PDO::FETCH_ASSOC);
} catch (Throwable $e) {
    error_log('resultats.php : ' . $e->getMessage());
    http_response_code(500);
    exit('Résultats indisponibles pour le moment.');
}

$totalVotes = array_sum(array_map(fn($l) => (int) $l['total'], $lignes));
$gagnant = $lignes[0]['candidat'] ?? null;
if (count($lignes) > 1 && (int) $lignes[0]['total'] === (int) $lignes[1]['total']) {
    $gagnant = null;                      // égalité : pas de gagnant
}

function e(string $texte): string
{
    return htmlspecialchars($texte, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="5">
    <title>Résultats des votes</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
            integrity="sha384-9nhczxUqK87bcKHh20fSQcTGD4qq5GhayNYSYWqwBkINBhOfQLg/P5HG5lF1urn4"
            crossorigin="anonymous"></script>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background: #f4f4f4; color: #333; padding: 20px; }
        h2 { color: #0077cc; }
        table { margin: auto; border-collapse: collapse; width: 70%; background: #fff; box-shadow: 0 0 10px rgba(0,0,0,.1); }
        th, td { padding: 12px; border: 1px solid #ddd; }
        th { background-color: #0077cc; color: white; }
        canvas { max-width: 420px; margin: 24px auto; }
    </style>
</head>
<body>
    <h2>Résultats des votes</h2>
<?php if ($totalVotes === 0): ?>
    <p>Aucun vote enregistré pour le moment.</p>
<?php else: ?>
    <table>
        <tr><th>Candidat</th><th>Votes</th><th>Pourcentage</th></tr>
<?php foreach ($lignes as $l): ?>
        <tr>
            <td><?= e($l['candidat']) ?></td>
            <td><?= (int) $l['total'] ?></td>
            <td><?= number_format(100 * (int) $l['total'] / $totalVotes, 1, ',', ' ') ?> %</td>
        </tr>
<?php endforeach; ?>
    </table>
    <p><?= $gagnant !== null ? 'En tête : <strong>' . e($gagnant) . '</strong>' : 'Égalité' ?> (<?= $totalVotes ?> votes)</p>
    <canvas id="graphique"></canvas>
    <script>
        new Chart(document.getElementById('graphique'), {
            type: 'pie',
            data: {
                labels: <?= json_encode(array_column($lignes, 'candidat'), JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_UNICODE) ?>,
                datasets: [{ data: <?= json_encode(array_map(fn($l) => (int) $l['total'], $lignes)) ?> }]
            }
        });
    </script>
<?php endif; ?>
</body>
</html>
