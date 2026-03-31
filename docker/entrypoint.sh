#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

host = ''
port = ''
database_url = os.getenv('DATABASE_URL', '')
if database_url:
    parsed = urlparse(database_url)
    host = parsed.hostname or ''
    port = parsed.port or 5432
elif os.getenv('USE_POSTGRES', 'False').lower() in {'1', 'true', 'yes', 'on'}:
    host = os.getenv('POSTGRES_HOST', 'db')
    port = int(os.getenv('POSTGRES_PORT', '5432'))

if host:
    deadline = time.time() + int(os.getenv('DB_WAIT_TIMEOUT', '60'))
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                sys.exit(0)
        except OSError:
            time.sleep(2)
    raise SystemExit(f'No fue posible conectar a la base de datos en {host}:{port}')
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${DJANGO_LOAD_SEED:-0}" = "1" ]; then
    python manage.py seed_congente_survey
fi

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -