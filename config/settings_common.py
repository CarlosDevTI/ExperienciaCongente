import os
from pathlib import Path
from urllib.parse import urlparse

from .env import load_env_file


BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR / '.env')


def env(key, default=None):
    return os.getenv(key, default)


def env_bool(key, default=False):
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


def env_list(key, default=''):
    return [item.strip() for item in env(key, default).split(',') if item.strip()]


def build_database_config():
    database_url = env('DATABASE_URL')
    if database_url:
        parsed = urlparse(database_url)
        engine_map = {
            'postgres': 'django.db.backends.postgresql',
            'postgresql': 'django.db.backends.postgresql',
            'pgsql': 'django.db.backends.postgresql',
            'sqlite': 'django.db.backends.sqlite3',
        }
        return {
            'ENGINE': engine_map.get(parsed.scheme, 'django.db.backends.postgresql'),
            'NAME': parsed.path.lstrip('/') or BASE_DIR / 'db.sqlite3',
            'USER': parsed.username or '',
            'PASSWORD': parsed.password or '',
            'HOST': parsed.hostname or '',
            'PORT': parsed.port or '',
        }

    if env_bool('USE_POSTGRES', default=False):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('POSTGRES_DB', 'congente_surveys'),
            'USER': env('POSTGRES_USER', 'postgres'),
            'PASSWORD': env('POSTGRES_PASSWORD', 'postgres'),
            'HOST': env('POSTGRES_HOST', 'localhost'),
            'PORT': env('POSTGRES_PORT', '5432'),
        }

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }


SECRET_KEY = env('DJANGO_SECRET_KEY', 'django-insecure-congente-dev-key')
DEBUG = env_bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', '')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'surveys',
    'dashboard',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {'default': build_database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/admin/login/'

CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=False)
CSRF_COOKIE_SAMESITE = env('CSRF_COOKIE_SAMESITE', 'Lax')
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env('SESSION_COOKIE_SAMESITE', 'Lax')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', env('SECURE_PROXY_SSL_HEADER_PROTO', 'https'))
USE_X_FORWARDED_HOST = env_bool('USE_X_FORWARDED_HOST', default=True)
SECURE_CONTENT_TYPE_NOSNIFF = env_bool('SECURE_CONTENT_TYPE_NOSNIFF', default=not DEBUG)
SECURE_REFERRER_POLICY = env('SECURE_REFERRER_POLICY', 'same-origin')
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', 'DENY')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '%(levelname)s %(asctime)s %(name)s %(message)s'},
        'simple': {'format': '%(levelname)s %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'root': {'handlers': ['console'], 'level': env('DJANGO_LOG_LEVEL', 'INFO')},
}

SURVEY_SESSION_COOKIE = 'congente_survey_session'
SURVEY_SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
APP_BASE_URL = env('APP_BASE_URL', 'http://127.0.0.1:8000')