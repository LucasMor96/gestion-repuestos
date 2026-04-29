from django.contrib import admin
from .models import (
    Tecnico, Proveedor, Producto, Pedido, Credito,
    CalificacionProveedor, CalificacionTecnico
)


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'especialidad', 'ubicacion', 'get_user_active', 'is_approved')
    search_fields = ('usuario__username', 'especialidad')
    list_filter = ('is_approved', 'usuario__is_active')
    readonly_fields = ('usuario',)

    def get_user_active(self, obj):
        return obj.usuario.is_active
    get_user_active.short_description = 'Activo'
    get_user_active.boolean = True


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_negocio', 'rubro', 'direccion', 'get_user_active', 'is_approved')
    search_fields = ('nombre_negocio', 'rubro', 'usuario__username')
    list_filter = ('is_approved', 'usuario__is_active')
    readonly_fields = ('usuario',)

    def get_user_active(self, obj):
        return obj.usuario.is_active
    get_user_active.short_description = 'Activo'
    get_user_active.boolean = True


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proveedor', 'categoria', 'precio', 'disponible')
    search_fields = ('nombre', 'categoria', 'proveedor__nombre_negocio')
    list_filter = ('disponible', 'categoria', 'proveedor')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tecnico', 'proveedor', 'producto', 'cantidad', 'estado')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio', 'producto__nombre')
    list_filter = ('estado', 'forma_entrega', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'proveedor', 'limite', 'saldo_usado')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio')
    list_filter = ('proveedor',)
    readonly_fields = ('tecnico', 'proveedor')


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
