from django.core.paginator import Paginator


PRODUCTOS_POR_PAGINA = 24


def paginar_productos(request, productos):
    pagina = Paginator(productos, PRODUCTOS_POR_PAGINA).get_page(request.GET.get('page'))
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return pagina, parametros.urlencode()
