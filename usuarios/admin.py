from django.contrib import admin

from .models import Proveedor, Tecnico


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'especialidad', 'ubicacion', 'get_user_active', 'is_approved')
    search_fields = ('usuario__username', 'especialidad')
    list_filter = ('is_approved', 'usuario__is_active')
    readonly_fields = ('usuario',)

    @admin.display(boolean=True, description='Activo')
    def get_user_active(self, obj):
        return obj.usuario.is_active


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_negocio', 'rubro', 'direccion', 'alias_transferencia', 'get_user_active', 'is_approved')
    search_fields = ('nombre_negocio', 'rubro', 'usuario__username')
    list_filter = ('is_approved', 'usuario__is_active')

    @admin.display(boolean=True, description='Activo')
    def get_user_active(self, obj):
        return obj.usuario.is_active
