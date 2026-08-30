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
?><!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso | <?= htmlspecialchars(APP_NAME) ?></title><link rel="stylesheet" href="style.css"></head><body class="auth"><main class="auth-card"><div class="brand-mark">LD</div><p class="eyebrow">LIBERATE DE TUS DEUDAS.CL</p><h1>Tu centro de conversaciones</h1><p class="auth-intro">Ingresa para gestionar de forma clara y segura la comunicación con tus clientes.</p><?php if ($error): ?><p class="alert"><?= htmlspecialchars($error) ?></p><?php endif; ?><form method="post"><input type="hidden" name="csrf" value="<?= htmlspecialchars(csrf_token()) ?>"><label>Usuario<input name="login" required autocomplete="username" placeholder="Tu usuario"></label><label>Contraseña<input type="password" name="password" required autocomplete="current-password" placeholder="Tu contraseña"></label><button>Ingresar al panel</button></form><small class="security-note">Acceso protegido · 2FA preparado</small></main></body></html>
