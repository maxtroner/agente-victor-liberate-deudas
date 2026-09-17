# Recopilación del proyecto

## Landing web

- Landing principal en `index.html`.
- Diseño responsive para escritorio y móvil.
- Logo, datos de contacto y llamados a WhatsApp.
- FAQ ampliado sobre renegociación, liquidación, Dicom y defensas judiciales.
- El contenido legal se presenta como orientación general y requiere evaluación individual.

## Agente de WhatsApp

- `app.py` recibe mensajes de WhatsApp Cloud API.
- Usa DeepSeek como modelo y Google Sheets como base de conocimiento.
- Usa Redis para historial temporal de conversaciones.
- Registra mensajes y datos de clientes en la plataforma PHP.
- Tiene modo de monitoreo y reenvío al administrador.
- Se corrigió el flujo del primer mensaje para responder preguntas directas.
- Se corrigió el manejo de `[NO_SE]` para que no se muestre al cliente.

## Plataforma estable

- Código en `platform/`.
- Login de usuarios, clientes, conversaciones, notas y respuestas manuales.
- Panel de escritorio en `dashboard.php`.
- Panel móvil en `dashmovil.php`.
- Base de datos MySQL con tablas de usuarios, clientes y conversaciones.
- La beta antigua fue eliminada y no forma parte del proyecto.

## Intervención manual

- Botón `Responder yo` disponible en escritorio y móvil.
- Al activarlo, el cliente pasa a modo humano.
- El agente consulta ese estado antes de generar una respuesta.
- Mientras está activo, el mensaje se registra y se reenvía al administrador sin respuesta automática.
- El botón cambia a `Devolver al bot` para reactivar la automatización.
- El estado queda persistido en MySQL, por lo que no depende de la memoria temporal del agente.

## Despliegue

- El código se respalda en GitHub.
- Los commits recientes incluyen la mejora del agente, FAQ y eliminación de beta.
- La publicación automática en Hostinger aún debe configurarse mediante SFTP/SSH o GitHub Actions.
- `platform/config.php`, credenciales, tokens y secretos no deben subirse al repositorio.

## Migración necesaria

En una base de datos existente, ejecutar:

```sql
ALTER TABLE clients ADD COLUMN bot_mode ENUM('bot','human') NOT NULL DEFAULT 'bot' AFTER status;
CREATE INDEX idx_clients_bot_mode ON clients (bot_mode);
```

La migración debe ejecutarse una sola vez antes de usar el botón en producción.
