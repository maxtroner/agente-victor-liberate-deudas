# Plataforma Victor

Plataforma PHP independiente en `platform/`. Usa PDO/MySQL y conserva los nombres del agente: `Clientes`, `phone`, `name`, `email`, `user`, `assistant` y `liberate:chat_history:{phone}` como referencia de origen.

1. Importar `schema.sql`.
2. Definir `VICTOR_PLATFORM_DB_DSN`, `VICTOR_PLATFORM_DB_USER` y `VICTOR_PLATFORM_DB_PASSWORD` en el hosting.
3. Insertar usuarios `victor` y `tester` con hashes producidos por `password_hash('...', PASSWORD_DEFAULT)`; no se incluyen contraseñas en el código.
4. Servir esta carpeta desde PHP 8.1+ con PDO MySQL habilitado.

4. Definir `PLATFORM_INGEST_SECRET`, `META_WABA_TOKEN` y `META_WABA_PHONE_NUMBER_ID` en el hosting PHP. En Modal definir `PLATFORM_INGEST_URL` apuntando a `api/ingest.php` y el mismo secreto.

`api/ingest.php` acepta JSON con `phone`, `role`, `content`, opcionalmente `message_id`, `name` y `email`; exige `X-Platform-Ingest-Secret`. `api/reply.php` requiere sesión del rol `victor` y envía por WhatsApp Cloud API. Para una base existente, ejecutar el schema con el usuario de esa base y agregar `clients.status`/`clients.notes` si la tabla ya existía sin esas columnas. 2FA tiene columnas/configuración preparadas y permanece desactivado.
