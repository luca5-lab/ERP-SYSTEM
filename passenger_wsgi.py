import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Cambia 'usbtech_spa' por el nombre de tu carpeta de configuración si es distinta
os.environ['DJANGO_SETTINGS_MODULE'] = 'usbtech_spa.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()