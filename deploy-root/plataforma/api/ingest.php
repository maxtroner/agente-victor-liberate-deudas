<?php
declare(strict_types=1); require_once __DIR__ . '/../auth.php';
$secret = app_config()['ingest_secret']; $provided = $_SERVER['HTTP_X_PLATFORM_INGEST_SECRET'] ?? '';
if (!$secret || !hash_equals($secret, $provided)) json_response(['error' => 'No autorizado'], 401);
$data = json_decode(file_get_contents('php://input'), true) ?: [];
$phone = trim((string)($data['phone'] ?? '')); $content = trim((string)($data['content'] ?? '')); $role = $data['role'] ?? '';
if (!preg_match('/^\+?[0-9]{8,20}$/', $phone) || $content === '' || !in_array($role, ['user','assistant','system'], true)) json_response(['error' => 'Payload invalido'], 422);
$pdo = db(); $pdo->beginTransaction();
$stmt = $pdo->prepare('INSERT INTO clients (phone, name, email) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE name=COALESCE(NULLIF(VALUES(name), ""), name), email=COALESCE(NULLIF(VALUES(email), ""), email)');
$stmt->execute([$phone, trim((string)($data['name'] ?? '')), trim((string)($data['email'] ?? ''))]);
$stmt = $pdo->prepare('INSERT IGNORE INTO conversations (phone, role, content, whatsapp_message_id) VALUES (?, ?, ?, ?)');
$stmt->execute([$phone, $role, $content, $data['message_id'] ?? null]); $pdo->commit(); json_response(['status' => 'ok']);
