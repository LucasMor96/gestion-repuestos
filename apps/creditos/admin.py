from django.contrib import admin

from .models import Credito


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'proveedor', 'limite', 'saldo_usado')
    search_fields = ('tecnico__usuario__username', 'proveedor__nombre_negocio')
    list_filter = ('proveedor',)
    readonly_fields = ('tecnico', 'proveedor')
