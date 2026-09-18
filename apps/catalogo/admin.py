from django.contrib import admin

from .forms import ProductoAdminForm
from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoAdminForm
    list_select_related = ('proveedor',)
    list_display = ('nombre', 'proveedor', 'categoria', 'precio', 'stock', 'disponible')
    search_fields = ('nombre', 'categoria', 'proveedor__nombre_negocio')
    list_filter = ('disponible', 'categoria', 'proveedor')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Django envuelve el POST del formulario de cambio en transaction.atomic.
        # No bloquear el listado ni las acciones administrativas sin transacción.
        match = request.resolver_match
        if request.method == 'POST' and match and match.url_name == 'catalogo_producto_change':
            queryset = queryset.select_for_update(of=('self',))
        return queryset
