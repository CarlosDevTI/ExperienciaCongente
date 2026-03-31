"""
ASGI config for config project.
"""

import os
from pathlib import Path

from django.core.asgi import get_asgi_application

from config.env import load_env_file

load_env_file(Path(__file__).resolve().parent.parent / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_dev')

application = get_asgi_application()
