from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, render

from usuarios.utils import get_tecnico_o_403

from .models import Producto


@login_required(login_url='login')
def buscar_repuestos(request):
    """Búsqueda de repuestos por nombre, modelo o categoría (US-04)."""
    tecnico = get_tecnico_o_403(request)
    if tecnico is None:
        return redirect('dashboard')

    query = request.GET.get('q', '').strip()
    categoria_sel = request.GET.get('categoria', '').strip()
    orden = request.GET.get('orden', '')

    try:
        productos = (
            Producto.objects
            .filter(disponible=True)
            .select_related('proveedor')
            .annotate(
                unidades_vendidas=Sum(
                    'pedidos__cantidad',
                    filter=Q(pedidos__estado='completado'),
                    default=0,
                )
            )
        )

        if query:
            productos = productos.filter(
                Q(nombre__icontains=query) |
                Q(modelo__icontains=query) |
                Q(categoria__icontains=query)
            )

        if categoria_sel:
            productos = productos.filter(categoria__icontains=categoria_sel)

        if orden == 'precio_asc':
            productos = productos.order_by('precio')
        elif orden == 'precio_desc':
            productos = productos.order_by('-precio')
        elif orden == 'mas_vendidos':
            productos = productos.order_by('-unidades_vendidas', 'nombre')

        categorias = (
            Producto.objects
            .filter(disponible=True)
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )

        productos_lista = list(productos)

        context = {
            'productos': productos_lista,
            'query': query,
            'categoria_sel': categoria_sel,
            'orden': orden,
            'categorias': categorias,
            'es_tecnico': hasattr(request.user, 'tecnico'),
        }
    except Exception:
        messages.error(request, 'Ocurrió un error al realizar la búsqueda. Intentá de nuevo.')
        context = {
            'productos': [],
            'query': query,
            'categoria_sel': categoria_sel,
            'orden': orden,
            'categorias': [],
            'es_tecnico': hasattr(request.user, 'tecnico'),
        }

    return render(request, 'catalogo/buscar_repuestos.html', context)
