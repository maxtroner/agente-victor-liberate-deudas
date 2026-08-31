<?php
declare(strict_types=1);

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
        'db_dsn' => env_value('VICTOR_PLATFORM_DB_DSN'),
        'db_user' => env_value('VICTOR_PLATFORM_DB_USER'),
        'db_password' => env_value('VICTOR_PLATFORM_DB_PASSWORD'),
        'two_factor_enabled' => TWO_FACTOR_ENABLED,
        'ingest_secret' => env_value('PLATFORM_INGEST_SECRET'),
        'meta_token' => env_value('META_WABA_TOKEN'),
        'meta_phone_id' => env_value('META_WABA_PHONE_NUMBER_ID'),
    ];
}
