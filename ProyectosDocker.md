# Despliegue Docker - Encuesta Congente

## Contexto objetivo

Este proyecto debe desplegarse en el servidor dockerizado `15.215`, no en la VM tradicional `15.41`.

Del inventario actual de contenedores se observan estos puertos publicados: `8000`, `8002`, `8004`, `8006`, `8008`, `8010`, `8011`, `8040`, `8080`.

Para evitar colisiones, esta app queda propuesta en el puerto:

- `8012` para Nginx del proyecto

Si en `15.215` ese puerto ya estuviera ocupado, solo cambia `NGINX_PUBLIC_PORT` en `.env`.

## Archivos de despliegue incluidos

- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `docker/nginx/default.conf`
- `.dockerignore`

## Arquitectura de produccion

Servicios en `docker-compose`:

- `db`: PostgreSQL 15 Alpine
- `web`: Django + Gunicorn
- `nginx`: reverse proxy, static y media

Flujo:

1. Nginx recibe trafico en `8012`
2. Nginx sirve `/static/` desde `staticfiles`
3. Nginx sirve `/media/` desde `media`
4. Nginx proxya el resto a Gunicorn (`web:8000`)
5. Gunicorn sirve Django en modo produccion

## Variables de entorno minimas para produccion

Crea `.env` en el servidor con algo como esto:

```env
DJANGO_SETTINGS_MODULE=config.settings_prod
DJANGO_SECRET_KEY=CAMBIA_ESTA_CLAVE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=15.215,tu-dominio.com,www.tu-dominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
USE_POSTGRES=True
POSTGRES_DB=congente_surveys
POSTGRES_USER=congente_user
POSTGRES_PASSWORD=CAMBIA_ESTA_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_LOG_LEVEL=INFO
APP_BASE_URL=https://tu-dominio.com
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
SECURE_SSL_REDIRECT=True
USE_X_FORWARDED_HOST=True
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=120
NGINX_PUBLIC_PORT=8012
DJANGO_LOAD_SEED=0
DB_WAIT_TIMEOUT=60
```

Notas:

- No hardcodees secretos en `docker-compose.yml`.
- `APP_BASE_URL` debe apuntar al dominio productivo real para generar URLs y QRs correctos.
- Si el TLS termina antes de este stack, mantén `X-Forwarded-Proto` bien configurado.

## Paso a paso de despliegue en servidor

### 1. Clonar el repositorio

```bash
git clone <REPO_URL> experiencia-usuario
cd experiencia-usuario
```

### 2. Crear `.env`

```bash
cp .env.example .env
nano .env
```

Ajusta dominio, secret key, hosts y credenciales.

### 3. Construir contenedores

```bash
docker compose build
```

### 4. Levantar servicios

```bash
docker compose up -d
```

### 5. Verificar estado

```bash
docker compose ps
```

### 6. Ejecutar migraciones manualmente si necesitas forzarlas

```bash
docker compose exec web python manage.py migrate
```

### 7. Crear superusuario

```bash
docker compose exec web python manage.py createsuperuser
```

### 8. Cargar semilla inicial si la base esta vacia

```bash
docker compose exec web python manage.py seed_congente_survey
```

### 9. Generar QR con dominio productivo

```bash
docker compose exec web python manage.py generate_qr_pngs
```

Ese comando usa `APP_BASE_URL` por defecto.

### 10. Ver logs

```bash
docker compose logs -f web
docker compose logs -f nginx
```

### 11. Validar acceso

Abre:

```text
http://IP_DEL_SERVIDOR:8012/dashboard/
```

o el dominio configurado si ya tienes proxy externo:

```text
https://tu-dominio.com/dashboard/
```

## Flujo de actualizacion con Git

Cuando haya cambios:

```bash
cd experiencia-usuario
git pull
docker compose build
docker compose up -d
```

Luego, si hubo cambios de esquema:

```bash
docker compose exec web python manage.py migrate
```

## Buenas practicas aplicadas

- Imagen base ligera: `python:3.12-slim`
- Gunicorn en produccion
- Nginx separado para reverse proxy y estaticos
- Variables sensibles via `.env`
- `restart: always`
- Logs a stdout/stderr para `docker compose logs`
- `collectstatic` automatico en `entrypoint.sh`
- Migraciones automaticas al arrancar `web`
- No se sirven estaticos con Django en produccion

## Gunicorn

Configuracion actual por variables:

- `GUNICORN_WORKERS=3`
- `GUNICORN_TIMEOUT=120`

Ajuste recomendado:

- VM pequena: `2` o `3` workers
- VM mediana: `3` a `5` workers

## Tokens y QR en produccion

### Token

Cada `QrEntryPoint` genera automaticamente un token unico con `UUID4`.

Caracteristicas:

- No es fijo globalmente
- No es secuencial
- No cambia por visita
- Identifica de forma unica el origen del QR
- Se asocia al `QrEntryPoint` y, por tanto, al area y punto de atencion

Ejemplo de URL final:

```text
https://tu-dominio.com/encuesta/caja/550e8400-e29b-41d4-a716-446655440000/
```

### Regenerar token o QR

Rotar token de un punto:

```bash
docker compose exec web python manage.py create_qr_entrypoint encuesta-satisfaccion-2026 caja "Caja" --rotate-token
```

Listar URLs activas:

```bash
docker compose exec web python manage.py list_qr_entrypoints
```

Generar PNG QR:

```bash
docker compose exec web python manage.py generate_qr_pngs
```

Los PNG quedan en:

- `media/qrcodes/`

## Seguridad del flujo de encuesta

Ya implementado en la app:

- CSRF activo
- Validacion backend de formularios
- Sanitizacion de texto abierto
- Cookie propia por sesion de encuesta
- Bloqueo de reenvio accidental cuando el QR no admite multiples respuestas
- Cabeceras `no-store` y `no-cache` en landing, pasos y pantalla final
- Persistencia por `session_uuid + qr_entry_point`

### Comportamiento esperado

- Si el usuario ya completo la encuesta con la misma sesion y el QR es de una sola respuesta: ve pantalla final, no puede duplicar envio.
- Si el usuario dejo la encuesta en progreso: retoma su `SurveySubmission` existente.
- Si vuelve atras en el navegador: no se deben cachear los pasos ni reenviar formularios automaticamente.

## Estaticos y media

Nginx sirve:

- `/static/` desde `staticfiles`
- `/media/` desde `media`

Django solo ejecuta `collectstatic`; no expone estaticos en produccion.

## Disponibilidad

Se usa:

- `restart: always`

Con eso, si Docker reinicia o el host se levanta de nuevo, el stack intenta volver automaticamente.

## Checklist final

- `.env` listo
- `APP_BASE_URL` apunta al dominio real
- `DJANGO_ALLOWED_HOSTS` correcto
- `DJANGO_CSRF_TRUSTED_ORIGINS` correcto
- `docker compose up -d` sin errores
- `docker compose logs -f web` sin fallos de migracion
- `/dashboard/` accesible
- `/encuesta/<area>/<token>/` accesible
- QR regenerados con dominio productivo