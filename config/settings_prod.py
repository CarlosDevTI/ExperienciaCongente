from .settings_common import *  # noqa: F403,F401
from .settings_common import env, env_bool

DEBUG = env_bool('DJANGO_DEBUG', default=False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=True)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = int(env('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', default=True)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
SECURE_REFERRER_POLICY = env('SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin')
SECURE_CONTENT_TYPE_NOSNIFF = env_bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)