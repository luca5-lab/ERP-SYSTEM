from django.contrib import admin
from .models import CotizacionArticulo, DetalleCotizacionArticulo, Proceso

# Esto hará que aparezcan en el panel /admin
admin.site.register(CotizacionArticulo)
admin.site.register(DetalleCotizacionArticulo)
