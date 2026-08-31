<?php
declare(strict_types=1);

// Configure these values in the hosting environment, never in source control.
const APP_NAME = 'Liberate de tus Deudas.cl';
const TWO_FACTOR_ENABLED = false;

function env_value(string $name, string $default = ''): string
{
    $value = getenv($name);
    return $value === false ? $default : $value;
}

function app_config(): array
{
    return [
        'db_dsn' => env_value('VICTOR_PLATFORM_DB_DSN', 'mysql:host=localhost;port=3306;dbname=u628813570_victorcrm;charset=utf8mb4'),
        'db_user' => env_value('VICTOR_PLATFORM_DB_USER', 'u628813570_victorcrm'),
        'db_password' => env_value('VICTOR_PLATFORM_DB_PASSWORD', 'Vt9!qR7#Lm2@Xc8$'),
        'two_factor_enabled' => TWO_FACTOR_ENABLED,
        'ingest_secret' => env_value('PLATFORM_INGEST_SECRET', 'liberate-ingest-2026-8f4c2a9e7b1d'),
        'meta_token' => env_value('META_WABA_TOKEN'),
        // Keep the public WhatsApp phone-number ID available if PHP-FPM does not inherit env vars.
        'meta_phone_id' => env_value('META_WABA_PHONE_NUMBER_ID', '1250371038140082'),
    ];
}
