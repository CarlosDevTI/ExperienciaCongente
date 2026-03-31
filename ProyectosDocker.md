# Despliegue Docker - Encuesta Congente

## Contexto objetivo

Este proyecto debe desplegarse en el servidor dockerizado `15.215`, no en la VM tradicional `15.41`.

Del inventario actual de contenedores se observan estos puertos publicados: `8000`, `8002`, `8004`, `8006`, `8008`, `8010`, `8011`, `8040`, `8080`.

Para evitar colisiones, esta app queda propuesta en el puerto:

- `8012` para Nginx del proyecto en `15.215`
- `8043` para publicacion HTTPS desde el proxy externo en `15.41`

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

1. Nginx del stack escucha en `8012`
2. Nginx sirve `/static/` desde `staticfiles`
3. Nginx sirve `/media/` desde el bind mount `./media`
4. Nginx proxya el resto a Gunicorn (`web:8000`)
5. Gunicorn sirve Django en modo produccion
6. El proxy externo en `15.41` publica `https://consulta.congente.coop:8043`

## Persistencia de media y QR

El stack ya queda configurado para persistir media en el host:

- Host: `./media`
- Contenedor: `/app/media`

Eso significa que los QR generados se guardan realmente en:

- `/home/sa/ExperienciaCongente/media/qrcodes/`

Y ademas se pueden servir por navegador en:

- `http://192.168.15.215:8012/media/qrcodes/<archivo>.png`
- `https://consulta.congente.coop:8043/media/qrcodes/<archivo>.png`

## Variables de entorno minimas para produccion

Ejemplo final para tu escenario con proxy externo:

```env
DJANGO_SETTINGS_MODULE=config.settings_prod
DJANGO_SECRET_KEY=CAMBIA_ESTA_CLAVE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=192.168.15.215,consulta.congente.coop,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://consulta.congente.coop:8043,http://192.168.15.215:8012
USE_POSTGRES=True
POSTGRES_DB=congente_surveys
POSTGRES_USER=congente_user
POSTGRES_PASSWORD=CAMBIA_ESTA_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_LOG_LEVEL=INFO
APP_BASE_URL=https://consulta.congente.coop:8043
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
SECURE_SSL_REDIRECT=False
USE_X_FORWARDED_HOST=True
SECURE_PROXY_SSL_HEADER_PROTO=https
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=120
NGINX_PUBLIC_PORT=8012
DJANGO_LOAD_SEED=0
DB_WAIT_TIMEOUT=60
```

Notas:

- `APP_BASE_URL` debe quedar con el dominio publico final para que los QR salgan listos para distribuir.
- Si accedes directo por IP temporalmente, puedes usar `APP_BASE_URL=http://192.168.15.215:8012` y luego regenerar QR cuando el dominio este activo.
- No hardcodees secretos en `docker-compose.yml`.
- Si tu `DJANGO_SECRET_KEY` contiene `$`, escapa cada uno como `$$` o usa una clave sin `$` para evitar warnings de Compose.

## Paso a paso de despliegue en servidor 15.215

### 1. Clonar el repositorio

```bash
git clone <REPO_URL> ExperienciaCongente
cd ExperienciaCongente
```

### 2. Crear `.env`

```bash
cp .env.example .env
nano .env
```

### 3. Crear carpeta media local del proyecto

```bash
mkdir -p media/qrcodes
```

### 4. Construir contenedores

```bash
docker compose build
```

### 5. Levantar servicios

```bash
docker compose up -d
```

### 6. Ejecutar migraciones

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

### 9. Generar QR apuntando al dominio productivo

```bash
docker compose exec web python manage.py generate_qr_pngs --survey=encuesta-satisfaccion-2026
```

### 10. Confirmar archivos en host

```bash
ls -lah media/qrcodes/
```

### 11. Verificar descarga directa

Abrir en navegador alguno de estos:

```text
http://192.168.15.215:8012/media/qrcodes/<archivo>.png
https://consulta.congente.coop:8043/media/qrcodes/<archivo>.png
```

## Proxy externo en 15.41

En el Nginx del servidor `15.41`, agrega un bloque equivalente a este:

```nginx
server {
    listen 8043 ssl;
    server_name consulta.congente.coop;

    ssl_certificate /ruta/cert.pem;
    ssl_certificate_key /ruta/key.pem;

    location / {
        proxy_pass http://192.168.15.215:8012;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Punto importante:

- El Nginx interno en `15.215` ya esta preparado para conservar `X-Forwarded-Proto=https` cuando venga desde `15.41`.

## Flujo de actualizacion con Git

```bash
cd ~/ExperienciaCongente
git pull
docker compose build
docker compose up -d
```

Si hubo cambios de esquema:

```bash
docker compose exec web python manage.py migrate
```

Si cambiaste dominio o `APP_BASE_URL`, regenera los QR:

```bash
docker compose exec web python manage.py generate_qr_pngs --survey=encuesta-satisfaccion-2026
```

## Tokens y QR en produccion

### Flujo correcto

1. Crear encuesta (`Survey`) o ejecutar seed
2. Crear areas (`Area`) o ejecutar seed
3. Crear `QrEntryPoint` por area
4. Cada `QrEntryPoint` genera su token UUID automaticamente
5. `generate_qr_pngs` toma esos entry points y crea los PNG

### Comandos utiles

Listar URLs activas:

```bash
docker compose exec web python manage.py list_qr_entrypoints --survey=encuesta-satisfaccion-2026
```

Regenerar token de un punto:

```bash
docker compose exec web python manage.py create_qr_entrypoint encuesta-satisfaccion-2026 caja "Caja" --rotate-token
```

Generar QR para una encuesta:

```bash
docker compose exec web python manage.py generate_qr_pngs --survey=encuesta-satisfaccion-2026
```

Generar para todas las encuestas activas:

```bash
docker compose exec web python manage.py generate_qr_pngs --all-surveys
```

## Seguridad del flujo de encuesta

Ya implementado en la app:

- CSRF activo
- Validacion backend de formularios
- Sanitizacion de texto abierto
- Cookie propia por sesion de encuesta
- Bloqueo de reenvio accidental cuando el QR no admite multiples respuestas
- Cabeceras `no-store` y `no-cache` en landing, pasos y pantalla final
- Persistencia por `session_uuid + qr_entry_point`

## Checklist final

- `.env` listo
- `APP_BASE_URL` apunta a `https://consulta.congente.coop:8043`
- `DJANGO_ALLOWED_HOSTS` incluye `192.168.15.215` y `consulta.congente.coop`
- `DJANGO_CSRF_TRUSTED_ORIGINS` incluye `https://consulta.congente.coop:8043`
- `docker compose up -d` sin errores
- `media/qrcodes/` existe en el host
- `http://192.168.15.215:8012/media/qrcodes/<archivo>.png` responde
- `https://consulta.congente.coop:8043/media/qrcodes/<archivo>.png` responde
- `/dashboard/` accesible
- `/encuesta/<area>/<token>/` accesible
- QR listos para distribucion publica