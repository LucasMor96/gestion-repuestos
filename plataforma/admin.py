from django.contrib import admin
from .models import Tecnico, Proveedor, Producto, Credito

admin.site.register(Tecnico)
admin.site.register(Proveedor)
admin.site.register(Producto)
admin.site.register(Credito)
