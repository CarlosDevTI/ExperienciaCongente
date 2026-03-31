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
python manage.py list_qr_entrypoints
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
- `DJANGO_CSRF_TRUSTED_ORIGINS`: orígenes HTTPS confiables separados por coma
- `DATABASE_URL`: URL completa de base de datos o usar las variables `POSTGRES_*`
- `USE_POSTGRES`: activa configuracion PostgreSQL por variables separadas
- `DJANGO_LOG_LEVEL`: nivel de logging
- `APP_BASE_URL`: host base para imprimir URLs y exportar PNG QR
- `GUNICORN_WORKERS`: numero de workers para produccion Docker
- `GUNICORN_TIMEOUT`: timeout Gunicorn en segundos
- `NGINX_PUBLIC_PORT`: puerto publicado por Nginx en Docker

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

En otras palabras:

- No cambia por cada visita del usuario.
- No cambia por cada submit.
- Si vuelves a usar el mismo `QrEntryPoint`, el token sigue siendo el mismo.
- Solo cambia si creas un QR nuevo o ejecutas `create_qr_entrypoint --rotate-token`.

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

## Los tokens actuales son definitivos o de prueba?

Los tokens que ves hoy en tu base local son los tokens activos reales de ese entorno local. No son "temporales por visita". Son estables hasta que:

- corras `create_qr_entrypoint --rotate-token`, o
- elimines/recrees el `QrEntryPoint`, o
- uses otra base de datos.

## Que URL debe usarse para generar el QR?

Debe usarse la URL publica completa, incluyendo host, area y token. Ejemplo local:

```text
http://127.0.0.1:8000/encuesta/caja/550e8400-e29b-41d4-a716-446655440000/
```

Ese es el valor que debe codificarse dentro del QR.

## El sistema genera el QR automaticamente?

Si. El proyecto ya puede generar PNGs QR de forma automatica con este comando:

```bash
python manage.py generate_qr_pngs
```

Salida:

- Crea archivos PNG en `media/qrcodes/`
- Genera uno por cada `QrEntryPoint` activo
- Cada PNG apunta a su URL publica completa usando `APP_BASE_URL`

Si quieres rotar el token antes de regenerar el QR:

```bash
python manage.py create_qr_entrypoint encuesta-satisfaccion-2026 caja "Caja" --rotate-token
```

## Flujo publico completo

1. Ejecuta `python manage.py seed_congente_survey`.
2. Ejecuta `python manage.py list_qr_entrypoints`.
3. Copia una de las URLs activas.
4. Abrela en el navegador.
5. El flujo es:
   - landing del area
   - `POST` a `/encuesta/<area>/<token>/iniciar/`
   - redireccion a `/encuesta/<area>/<token>/paso/1/`
   - avance secuencial por `/paso/2/`, `/paso/3/`, etc.
   - pantalla final en `/encuesta/<area>/<token>/gracias/`

El estado se mantiene con una cookie propia (`congente_survey_session`) y un `SurveySubmission` asociado a ese `QrEntryPoint`. Si el usuario vuelve con la misma sesion, el sistema puede continuar o bloquear reenvio accidental segun la configuracion del QR. Las vistas de encuesta se sirven con `no-store` y `no-cache` para reducir problemas de reenvio por navegador.

## Preguntas por area

Las preguntas se asignan dinamicamente por `AreaQuestion` y se cargan segun el `area_slug` del QR activo:

- `caja`: `q1`, `q2`, `q7`, `q8`, `q9`, `q10`
- `asesoria`: `q1`, `q3`, `q7`, `q8`, `q9`, `q10`
- `servicio-asociado`: `q4`, `q7`, `q8`, `q9`, `q10`
- `servicio-convenios`: `q5`, `q6`, `q7`, `q8`, `q9`, `q10`

## URLs principales

- `/encuesta/<area>/<token>/`: landing publica por QR
- `/encuesta/<area>/<token>/paso/<n>/`: wizard publico HTMX
- `/dashboard/`: resumen interno
- `/dashboard/respuestas/`: listado filtrable
- `/admin/`: administracion tecnica

## Branding y assets

Los assets oficiales se sirven desde `static/brand/`:

- `logo.png`: navbar y sidebar
- `IconoHD.png`: favicon y marca de agua sutil

## Exportaciones

- CSV: `/dashboard/export/responses.csv`
- Excel: `/dashboard/export/responses.xlsx`

## Tests

```bash
python manage.py test
```

## Produccion Docker

Este repositorio ya incluye:

- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `docker/nginx/default.conf`

Despliegue resumido:

```bash
git clone <REPO_URL>
cd experiencia-usuario
cp .env.example .env
# editar .env para produccion

docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py generate_qr_pngs
```

La guia completa esta en `ProyectosDocker.md`.