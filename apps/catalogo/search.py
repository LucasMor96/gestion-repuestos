import logging

from django.db import DatabaseError
from django.shortcuts import redirect, render

from apps.usuarios.utils import get_tecnico_o_403

from .selectors import buscar_productos, categorias_publicadas

logger = logging.getLogger(__name__)


def buscar_repuestos(request):
    if request.user.is_authenticated and get_tecnico_o_403(request) is None:
        return redirect('dashboard')
    query = request.GET.get('q', '').strip()
    categoria_sel = request.GET.get('categoria', '').strip()
    orden = request.GET.get('orden', '')
    error_busqueda = ''
    try:
        productos = list(buscar_productos(
            texto=query, categoria=categoria_sel, orden=orden
        ))
        categorias = list(categorias_publicadas())
    except DatabaseError:
        logger.exception('No se pudo consultar el catálogo de repuestos.')
        productos = []
        categorias = []
        error_busqueda = 'Ocurrió un error al realizar la búsqueda. Volvé a intentarlo en unos momentos.'

    return render(request, 'catalogo/buscar_repuestos.html', {
        'productos': productos,
        'query': query,
        'categoria_sel': categoria_sel,
        'orden': orden,
        'categorias': categorias,
        'es_tecnico': request.user.is_authenticated,
        'error_busqueda': error_busqueda,
    }, status=503 if error_busqueda else 200)
