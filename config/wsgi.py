"""
WSGI config for config project.
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

from config.env import load_env_file

load_env_file(Path(__file__).resolve().parent.parent / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings_dev'))

application = get_wsgi_application()
