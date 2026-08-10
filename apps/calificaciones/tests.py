from django.contrib.auth.models import User
from django.test import TestCase

from apps.catalogo.models import Producto
from apps.pedidos.models import Pedido
from apps.usuarios.models import Proveedor, Tecnico

from .exceptions import ActorInvalido, CalificacionDuplicada, PedidoNoCompletado
from .services import calificar_proveedor, validar_calificacion_proveedor


class CalificacionServiceTests(TestCase):
    def setUp(self):
        self.tecnico = Tecnico.objects.create(
            usuario=User.objects.create_user(username='cal-tec'),
            especialidad='mecanica_automotriz', ubicacion='CABA',
        )
        self.otro_tecnico = Tecnico.objects.create(
            usuario=User.objects.create_user(username='cal-otro'),
            especialidad='mecanica_automotriz', ubicacion='CABA',
        )
        self.proveedor = Proveedor.objects.create(
            usuario=User.objects.create_user(username='cal-prov'),
            nombre_negocio='Calificaciones', direccion='CABA', rubro='mecanica_automotriz',
        )
        producto = Producto.objects.create(
            proveedor=self.proveedor, nombre='Filtro', categoria='mecanica_automotriz',
            precio=100, stock=1,
        )
        self.pedido = Pedido.objects.create(
            tecnico=self.tecnico, proveedor=self.proveedor, producto=producto,
            cantidad=1, forma_entrega='retiro', monto_total=100,
        )

    def test_exige_pedido_completado_y_actor_correcto(self):
        with self.assertRaises(PedidoNoCompletado):
            validar_calificacion_proveedor(pedido=self.pedido, tecnico=self.tecnico)
        self.pedido.estado = 'completado'
        self.pedido.save()
        with self.assertRaises(ActorInvalido):
            validar_calificacion_proveedor(pedido=self.pedido, tecnico=self.otro_tecnico)

    def test_no_permite_calificacion_duplicada_y_actualiza_promedio(self):
        self.pedido.estado = 'completado'
        self.pedido.save()
        calificar_proveedor(
            pedido=self.pedido, tecnico=self.tecnico, estrellas=5, comentario='Bien'
        )
        self.assertEqual(self.proveedor.calificacion_promedio, 5)
        with self.assertRaises(CalificacionDuplicada):
            calificar_proveedor(
                pedido=self.pedido, tecnico=self.tecnico, estrellas=4
            )
