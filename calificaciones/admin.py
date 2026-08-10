from django.contrib import admin

from .models import CalificacionProveedor, CalificacionTecnico


@admin.register(CalificacionProveedor)
class CalificacionProveedorAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'proveedor', 'estrellas', 'fecha_creacion')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio')
    list_filter = ('estrellas', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'tecnico', 'proveedor', 'pedido')


@admin.register(CalificacionTecnico)
class CalificacionTecnicoAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'tecnico', 'puntualidad', 'trato', 'fecha_creacion')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio')
    list_filter = ('puntualidad', 'trato', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'proveedor', 'tecnico', 'pedido')
