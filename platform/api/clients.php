<?php
declare(strict_types=1); require_once __DIR__ . '/../auth.php'; require_login();
$q = trim($_GET['q'] ?? ''); $stmt = db()->prepare('SELECT phone, name, email, status, notes, created_at, updated_at FROM clients WHERE phone LIKE ? OR name LIKE ? OR email LIKE ? ORDER BY updated_at DESC LIMIT 100'); $like = "%$q%"; $stmt->execute([$like, $like, $like]); json_response(['data' => $stmt->fetchAll()]);
