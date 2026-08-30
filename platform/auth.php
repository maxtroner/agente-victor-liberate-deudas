<?php
declare(strict_types=1);
require_once __DIR__ . '/db.php';

if (session_status() !== PHP_SESSION_ACTIVE) session_start();
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_samesite', 'Lax');
if (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ini_set('session.cookie_secure', '1');

function csrf_token(): string
{
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32));
    return $_SESSION['csrf'];
}

function require_csrf(): void
{
    if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) {
        http_response_code(419); exit('CSRF token inválido');
    }
}

function require_login(): array
{
    if (empty($_SESSION['user'])) { header('Location: index.php'); exit; }
    return $_SESSION['user'];
}

function require_role(string ...$roles): array
{
    $user = require_login();
    if (!in_array($user['role'] ?? '', $roles, true)) json_response(['error' => 'No autorizado'], 403);
    return $user;
}

function json_response(array $data, int $status = 200): never
{
    http_response_code($status); header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE); exit;
}
