<?php
declare(strict_types=1); require_once __DIR__ . '/../auth.php'; require_login();
$phone = trim($_GET['phone'] ?? ''); if (!preg_match('/^[0-9+]{8,20}$/', $phone)) json_response(['error' => 'Teléfono inválido'], 422);
$stmt = db()->prepare('SELECT id, phone, role, content, whatsapp_message_id, created_at FROM conversations WHERE phone = ? ORDER BY created_at ASC LIMIT 500'); $stmt->execute([$phone]); json_response(['data' => $stmt->fetchAll()]);
