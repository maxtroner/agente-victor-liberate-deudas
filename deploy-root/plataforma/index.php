<?php
declare(strict_types=1);
require_once __DIR__ . '/auth.php';
if (isset($_GET['logout'])) { session_destroy(); header('Location: index.php'); exit; }
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    require_csrf();
    $stmt = db()->prepare('SELECT id, username, password_hash, role, two_factor_enabled FROM users WHERE username = ? AND active = 1 LIMIT 1');
    $stmt->execute([trim($_POST['login'] ?? '')]); $user = $stmt->fetch();
    if ($user && password_verify($_POST['password'] ?? '', $user['password_hash'])) {
        unset($user['password_hash']); session_regenerate_id(true); $_SESSION['user'] = $user;
        header('Location: dashboard.php'); exit;
    }
    $error = 'Usuario o contraseña incorrectos.';
}
?><!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso | <?= htmlspecialchars(APP_NAME) ?></title><link rel="stylesheet" href="style.css"></head><body class="auth"><main class="card"><p class="eyebrow">PLATAFORMA VICTOR</p><h1>Acceso seguro</h1><?php if ($error): ?><p class="alert"><?= htmlspecialchars($error) ?></p><?php endif; ?><form method="post"><input type="hidden" name="csrf" value="<?= htmlspecialchars(csrf_token()) ?>"><label>Usuario<input name="login" required autocomplete="username"></label><label>Contraseña<input type="password" name="password" required autocomplete="current-password"></label><button>Ingresar</button></form><small>2FA preparado: inactivo</small></main></body></html>
