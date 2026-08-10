from .models import Producto


def productos_proveedor(proveedor):
    return Producto.objects.del_proveedor(proveedor).order_by('nombre')


def buscar_productos(*, texto='', categoria='', orden=''):
    return Producto.objects.buscar(texto=texto, categoria=categoria, orden=orden)


def categorias_publicadas():
    return Producto.objects.publicados().values_list(
        'categoria', flat=True
    ).distinct().order_by('categoria')
