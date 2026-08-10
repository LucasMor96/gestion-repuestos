from django.contrib import admin

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tecnico', 'proveedor', 'producto', 'cantidad', 'forma_pago', 'tiene_comprobante', 'estado')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio', 'producto__nombre')
    list_filter = ('estado', 'forma_entrega', 'forma_pago', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    @admin.display(boolean=True, description='Comprobante')
    def tiene_comprobante(self, obj):
        return bool(obj.comprobante_transferencia)
