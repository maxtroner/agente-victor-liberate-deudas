<?php
declare(strict_types=1);
require_once __DIR__ . '/auth.php';

function beta_bootstrap(): void
{
    static $ready = false;
    if ($ready) return;
    $pdo = db();
    $pdo->exec("CREATE TABLE IF NOT EXISTS beta_availability (id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, weekday TINYINT UNSIGNED NOT NULL UNIQUE, enabled TINYINT(1) NOT NULL DEFAULT 0, start_time TIME NULL, end_time TIME NULL, slot_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 30, buffer_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 10, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)");
    $pdo->exec("CREATE TABLE IF NOT EXISTS beta_appointments (id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, phone VARCHAR(20) NOT NULL, title VARCHAR(190) NOT NULL, starts_at DATETIME NOT NULL, ends_at DATETIME NOT NULL, status ENUM('held','confirmed','cancelled','completed','no_show') NOT NULL DEFAULT 'confirmed', notes TEXT NULL, created_by VARCHAR(80) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, INDEX idx_beta_appointments_time (starts_at, ends_at), INDEX idx_beta_appointments_phone (phone))");
    $pdo->exec("CREATE TABLE IF NOT EXISTS beta_summaries (phone VARCHAR(20) PRIMARY KEY, summary TEXT NOT NULL, next_action VARCHAR(190) NULL, updated_by VARCHAR(80) NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)");
    $stmt = $pdo->prepare('INSERT IGNORE INTO beta_availability (weekday, enabled, start_time, end_time) VALUES (?, ?, ?, ?)');
    for ($day = 1; $day <= 7; $day++) $stmt->execute([$day, $day <= 5 ? 1 : 0, $day <= 5 ? '09:00:00' : null, $day <= 5 ? '18:00:00' : null]);
    $ready = true;
}

function beta_json(array $data, int $status = 200): never
{
    http_response_code($status); header('Content-Type: application/json; charset=utf-8'); echo json_encode($data, JSON_UNESCAPED_UNICODE); exit;
}
