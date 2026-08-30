<?php
declare(strict_types=1); require_once __DIR__ . '/../auth.php'; require_login(); require_csrf();
$data = json_decode(file_get_contents('php://input'), true) ?: $_POST; $phone = trim((string)($data['phone'] ?? ''));
if (!preg_match('/^\+?[0-9]{8,20}$/', $phone)) json_response(['error' => 'Telefono invalido'], 422);
$allowed = ['new','open','pending','closed']; $status = (string)($data['status'] ?? 'open'); if (!in_array($status, $allowed, true)) json_response(['error' => 'Estado invalido'], 422);
$stmt = db()->prepare('UPDATE clients SET status=?, notes=? WHERE phone=?'); $stmt->execute([$status, trim((string)($data['notes'] ?? '')), $phone]); json_response(['status' => 'ok']);
