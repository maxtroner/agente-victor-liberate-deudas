<?php
declare(strict_types=1);
require_once __DIR__ . '/../auth.php';
require_role('victor', 'tester');
require_csrf();

$data = json_decode(file_get_contents('php://input'), true) ?: $_POST;
$phone = trim((string)($data['phone'] ?? ''));
$mode = (string)($data['mode'] ?? 'human');
if (!preg_match('/^\+?[0-9]{8,20}$/', $phone)) json_response(['error' => 'Telefono invalido'], 422);
if (!in_array($mode, ['bot', 'human'], true)) json_response(['error' => 'Modo invalido'], 422);

$stmt = db()->prepare('INSERT INTO clients (phone, bot_mode) VALUES (?, ?) ON DUPLICATE KEY UPDATE bot_mode = VALUES(bot_mode)');
$stmt->execute([$phone, $mode]);
json_response(['status' => 'ok', 'mode' => $mode]);
