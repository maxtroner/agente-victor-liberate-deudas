# Manual de respaldo y operación

## Identificadores

- Modal workspace: `maxtroner`
- Modal app: `liberate-deudas`
- Endpoint: `https://maxtroner--liberate-deudas-fastapi-app.modal.run`
- CRM: `https://www.liberatedetusdeudas.cl/plataforma/`
- Phone Number ID: `1250371038140082`
- WhatsApp Business Account ID: `1987836971845393`
- Número WhatsApp: `+56 9 2075 7276`
- Base MySQL: `u628813570_victorcrm`

## Arquitectura

WhatsApp -> Meta Cloud API -> Modal/FastAPI -> DeepSeek + Google Sheets + Upstash Redis -> WhatsApp.

Dashboard Victor -> PHP Hostinger -> Meta Cloud API.

## Estado logrado

- Agente desplegado en Modal.
- Health check confirmado.
- Google Sheets configurado como RAG.
- Historial temporal en Redis.
- Webhook Meta operativo.
- Dashboard PHP/MySQL operativo.
- Landing pública operativa en `/index.html` y en la raíz del dominio.
- Dashboard móvil operativo en `/plataforma/dashmovil.php`.
- Los dispositivos móviles que abren `dashboard.php` se redirigen automáticamente al dashboard móvil.
- Usuarios `victor` y `tester` pueden responder.
- Respuestas manuales verificadas.
- Secreto Hostinger fuera de `public_html`.
- Error de ruta corregido usando `/home/u628813570/.meta-secrets.php`.

## Secretos

El token real no se incluye en este manual ni en GitHub. En Hostinger está en:

`/home/u628813570/.meta-secrets.php`

Debe tener permisos `600`. El secreto de Modal se llama `liberate-deudas-secrets`.

## Despliegue Modal

```powershell
python -m modal token new
cd "C:\Users\MaxtronerPC\Documents\agosto 2026\agente victor"
python -m modal deploy app.py
```

Para modificar secretos, usar la interfaz de Modal y conservar todas las variables existentes. `create --force` reemplaza el secreto completo.

## Hostinger

`platform/config.php` debe cargar el secreto con ruta absoluta:

```php
$meta_file = '/home/u628813570/.meta-secrets.php';
```

El fallo histórico fue que `getenv('HOME')` estaba vacío en PHP web, generando la URL incorrecta `/v21.0//messages`.

## Uso

1. Entrar a la plataforma.
2. Seleccionar una conversación.
3. Escribir y enviar la respuesta.
4. El cliente debe haber escrito dentro de las últimas 24 horas para texto libre; después se necesita una plantilla aprobada por Meta.

En celular se puede usar directamente `https://www.liberatedetusdeudas.cl/plataforma/dashmovil.php`. Si se abre por error `dashboard.php`, la detección de Android/iPhone redirige automáticamente a la versión móvil. Dentro de un chat, el botón visual y el botón Atrás del dispositivo regresan al listado.

## Diagnóstico

```bash
grep -R "WhatsApp reply failed" /home/u628813570 2>/dev/null
```

El log del sitio está en:

`/home/u628813570/.logs/error_log_liberatedetusdeudas_cl`

## Seguridad y próximos pasos

- Rotar el token porque fue expuesto durante la sesión.
- No guardar tokens, contraseñas ni claves privadas en Obsidian, PDF o GitHub.
- Instalar Git y configurar el repositorio remoto para publicar el proyecto.
- Crear plantillas Meta para conversaciones fuera de 24 horas.
