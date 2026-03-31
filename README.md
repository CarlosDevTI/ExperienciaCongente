# Congente Survey 2026

Aplicacion Django mobile-first para encuesta de satisfaccion por QR, con flujo publico paso a paso y dashboard interno para analitica y exportacion.

## Stack

- Django 5
- PostgreSQL como base objetivo
- Django Templates + HTMX + Alpine.js
- Tailwind CSS via CDN para la primera version
- Chart.js para visualizaciones internas
- QR PNG opcional con `qrcode[pil]`
- Docker + Gunicorn + Nginx para produccion

## Modulos principales

- `surveys`: modelos, flujo publico, admin, seed y comandos de QR.
- `dashboard`: vistas internas, filtros, exportacion y detalle de respuestas.
- `analytics`: consultas agregadas para metricas y reportes.
- `core`: utilidades compartidas de auditoria.

## Configuracion local

1. Crear y activar entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear el archivo `.env` a partir de `.env.example`. El proyecto lo carga automaticamente al ejecutar `manage.py`, `wsgi.py` o `asgi.py`.
4. Ejecutar migraciones:

```bash
python manage.py migrate
```

5. Cargar datos semilla:

```bash
python manage.py seed_congente_survey
```

6. Listar URLs validas de prueba:

```bash
python manage.py list_qr_entrypoints --survey=encuesta-satisfaccion-2026
```

7. Crear superusuario:

```bash
python manage.py createsuperuser
```

8. Levantar servidor:

```bash
python manage.py runserver
```

## Variables de entorno

- `DJANGO_SETTINGS_MODULE`: `config.settings_dev` o `config.settings_prod`
- `DJANGO_SECRET_KEY`: clave secreta
- `DJANGO_DEBUG`: `True` o `False`
- `DJANGO_ALLOWED_HOSTS`: hosts separados por coma
- `DJANGO_CSRF_TRUSTED_ORIGINS`: origenes confiables separados por coma
- `DATABASE_URL`: URL completa de base de datos o usar las variables `POSTGRES_*`
- `USE_POSTGRES`: activa configuracion PostgreSQL por variables separadas
- `DJANGO_LOG_LEVEL`: nivel de logging
- `APP_BASE_URL`: host base para imprimir URLs y exportar PNG QR
- `GUNICORN_WORKERS`: numero de workers para produccion Docker
- `GUNICORN_TIMEOUT`: timeout Gunicorn en segundos
- `NGINX_PUBLIC_PORT`: puerto publicado por Nginx en Docker
- `SECURE_PROXY_SSL_HEADER_PROTO`: `http` o `https` segun el proxy aguas arriba

### Ejemplo minimo para desarrollo con SQLite

```env
DJANGO_SETTINGS_MODULE=config.settings_dev
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
USE_POSTGRES=False
DJANGO_LOG_LEVEL=INFO
APP_BASE_URL=http://127.0.0.1:8000
```

Con `USE_POSTGRES=False`, Django usa `db.sqlite3` en la raiz del proyecto. No necesitas exportar variables manualmente en PowerShell si ya existe el archivo `.env`.

## Como funciona el token y el QR

### 1. Creacion del QR entry point

Cada area tiene un `QrEntryPoint` activo. En esta version se mantiene uno por area:

- Caja
- Asesoria
- Servicio al asociado
- Servicio convenios

Puedes crearlo o actualizarlo con:

```bash
python manage.py create_qr_entrypoint encuesta-satisfaccion-2026 caja "Caja"
```

### 2. Generacion del token

El campo `public_token` se genera automaticamente con `uuid4`.

- Es un UUID unico por `QrEntryPoint`.
- No es secuencial.
- Se queda fijo para ese QR mientras no lo rotes manualmente.

### 3. Asociacion del token con el entry point

El token vive en el modelo `QrEntryPoint`. Eso permite rastrear el origen de cada respuesta porque cada `SurveySubmission` guarda el `qr_entry_point` que disparo el flujo.

### 4. Construccion de la URL final

La URL publica se arma asi:

```text
/encuesta/<area>/<token>/
```

Ejemplo:

```text
/encuesta/caja/550e8400-e29b-41d4-a716-446655440000/
```

## El sistema genera el QR automaticamente?

Si. El proyecto puede generar PNGs QR automaticamente con:

```bash
python manage.py generate_qr_pngs --survey=encuesta-satisfaccion-2026
```

O para todas las encuestas activas:

```bash
python manage.py generate_qr_pngs --all-surveys
```

Comportamiento:

- Crea archivos PNG en `media/qrcodes/`
- Usa `APP_BASE_URL` para construir la URL publica final
- Requiere que la encuesta exista y tenga `QrEntryPoint` activos
- Si hay varias encuestas activas y no indicas `--survey`, lista los slugs disponibles
- Si es una instalacion nueva, primero ejecuta `python manage.py seed_congente_survey`

## Flujo publico completo

1. Ejecuta `python manage.py seed_congente_survey`.
2. Ejecuta `python manage.py list_qr_entrypoints --survey=encuesta-satisfaccion-2026`.
3. Copia una de las URLs activas.
4. Abrela en el navegador.
5. El flujo es:
   - landing del area
   - `POST` a `/encuesta/<area>/<token>/iniciar/`
   - redireccion a `/encuesta/<area>/<token>/paso/1/`
   - avance secuencial por `/paso/2/`, `/paso/3/`, etc.
   - pantalla final en `/encuesta/<area>/<token>/gracias/`

El estado se mantiene con una cookie propia (`congente_survey_session`) y un `SurveySubmission` asociado a ese `QrEntryPoint`. Si el usuario vuelve con la misma sesion, el sistema puede continuar o bloquear reenvio accidental segun la configuracion del QR. Las vistas de encuesta se sirven con `no-store` y `no-cache` para reducir problemas de reenvio por navegador.

## Produccion Docker

El stack publica la app en `http://IP:8012` y deja persistente `media/` en el host con el bind mount:

- Host: `./media`
- Contenedor: `/app/media`

Eso permite que los QR queden disponibles fisicamente en el servidor y se sirvan por Nginx en `/media/`.

Flujo resumido:

```bash
git clone <REPO_URL>
cd ExperienciaCongente
cp .env.example .env
mkdir -p media/qrcodes
# editar .env para produccion

docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_congente_survey
docker compose exec web python manage.py generate_qr_pngs --survey=encuesta-satisfaccion-2026
```

Guia completa:

- `ProyectosDocker.md`