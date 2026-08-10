from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proveedor', 'categoria', 'precio', 'stock', 'disponible')
    search_fields = ('nombre', 'categoria', 'proveedor__nombre_negocio')
    list_filter = ('disponible', 'categoria', 'proveedor')
