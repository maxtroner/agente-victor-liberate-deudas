<?php
declare(strict_types=1);
require_once __DIR__ . '/../auth.php';

$cfg = app_config();
$secret = (string)($cfg['ingest_secret'] ?? '');
if (!$secret || !hash_equals($secret, (string)($_SERVER['HTTP_X_PLATFORM_INGEST_SECRET'] ?? ''))) {
    json_response(['error' => 'No autorizado'], 401);
}

$phone = trim((string)($_GET['phone'] ?? ''));
if (!preg_match('/^\+?[0-9]{8,20}$/', $phone)) json_response(['error' => 'Telefono invalido'], 422);
$stmt = db()->prepare('SELECT bot_mode FROM clients WHERE phone = ? LIMIT 1');
$stmt->execute([$phone]);
$row = $stmt->fetch();
json_response(['mode' => $row['bot_mode'] ?? 'bot']);
