from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.models import Proveedor

from .models import Producto
from .selectors import buscar_productos


class CatalogoDomainTests(TestCase):
    def setUp(self):
        proveedor = Proveedor.objects.create(
            usuario=User.objects.create_user(username='cat-prov'),
            nombre_negocio='Catalogo', direccion='CABA', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        self.producto = Producto.objects.create(
            proveedor=proveedor, nombre='Filtro premium', modelo='X1',
            categoria='mecanica_automotriz', precio=1500, stock=2,
        )

    def test_busqueda_y_disponibilidad_viven_fuera_de_la_view(self):
        self.assertEqual(list(buscar_productos(texto='premium')), [self.producto])
        self.assertFalse(self.producto.alternar_disponibilidad())
        self.assertFalse(buscar_productos(texto='premium').exists())
