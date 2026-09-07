from unittest.mock import patch

from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from apps.calificaciones.models import CalificacionProveedor
from apps.pedidos.exceptions import ProveedorNoHabilitado
from apps.pedidos.models import Pedido
from apps.pedidos.services import cancelar_pedido, crear_pedido
from apps.pedidos.test_integridad import DatosPedidoMixin
from apps.usuarios.models import Proveedor
from apps.usuarios.services import cambiar_estado_perfil

from .models import Producto
from .selectors import buscar_productos, categorias_publicadas


class ConservacionHistorialTests(DatosPedidoMixin, TestCase):
    def test_producto_sin_pedidos_se_puede_eliminar(self):
        self.client.force_login(self.proveedor.usuario)
        respuesta = self.client.post(reverse('eliminar_producto', args=[self.producto.pk]))
        self.assertRedirects(respuesta, reverse('catalogo_proveedor'))
        self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_eliminacion_con_pedido_no_borra_historial_ni_altera_credito(self):
        pedido = self.comprar()
        self.client.force_login(self.proveedor.usuario)
        respuesta = self.client.post(reverse('eliminar_producto', args=[self.producto.pk]), follow=True)
        self.assertContains(respuesta, 'tiene pedidos asociados')
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.credito.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')
        self.assertEqual(self.credito.saldo_usado, 1000)
        cancelar_pedido(pedido=pedido)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    def test_proteccion_orm_y_borrado_masivo_para_todos_los_estados(self):
        pedido = self.comprar()
        for estado, _ in Pedido.ESTADO_CHOICES:
            with self.subTest(estado=estado):
                Pedido.objects.filter(pk=pedido.pk).update(estado=estado)
                with self.assertRaises(ProtectedError):
                    self.producto.delete()
                with self.assertRaises(ProtectedError):
                    Producto.objects.filter(pk=self.producto.pk).delete()
                self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_conserva_calificaciones_y_comprobante(self):
        pedido = self.comprar()
        pedido.estado = 'completado'
        pedido.comprobante_transferencia = 'comprobantes_transferencia/historico.pdf'
        pedido.save(update_fields=['estado', 'comprobante_transferencia'])
        calificacion = CalificacionProveedor.objects.create(
            pedido=pedido, tecnico=self.tecnico, proveedor=self.proveedor, estrellas=5,
        )
        with self.assertRaises(ProtectedError):
            self.producto.delete()
        self.assertTrue(CalificacionProveedor.objects.filter(pk=calificacion.pk).exists())
        pedido.refresh_from_db()
        self.assertEqual(pedido.comprobante_transferencia.name, 'comprobantes_transferencia/historico.pdf')

    def test_admin_tampoco_elimina_producto_con_pedidos(self):
        pedido = self.comprar()
        admin = User.objects.create_superuser(username='admin-integridad', password='test')
        self.client.force_login(admin)
        respuesta = self.client.post(reverse('admin:catalogo_producto_delete', args=[self.producto.pk]), {'post': 'yes'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_ocultar_conserva_pedidos_y_evitar_nuevas_compras(self):
        pedido = self.comprar()
        self.client.force_login(self.proveedor.usuario)
        self.client.post(reverse('toggle_disponibilidad', args=[self.producto.pk]))
        self.assertFalse(buscar_productos().exists())
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())
        self.client.force_login(self.tecnico.usuario)
        self.assertEqual(self.client.post(
            reverse('crear_pedido', args=[self.producto.pk]), self.datos(),
        ).status_code, 404)


class ProveedorHabilitadoTests(DatosPedidoMixin, TestCase):
    def test_estados_y_flags_excluyen_catalogo_y_bloquean_servicio(self):
        casos = [
            ('pendiente', True, True), ('rechazado', True, True),
            ('suspendido', True, True), ('aprobado', False, True),
            ('aprobado', True, False),
        ]
        for estado, aprobado, activo in casos:
            with self.subTest(estado=estado, aprobado=aprobado, activo=activo):
                Proveedor.objects.filter(pk=self.proveedor.pk).update(estado=estado, is_approved=aprobado)
                User.objects.filter(pk=self.proveedor.usuario_id).update(is_active=activo)
                self.assertFalse(buscar_productos().exists())
                self.assertFalse(categorias_publicadas().exists())
                for forma_pago, _ in Pedido.FORMA_PAGO_CHOICES:
                    with self.assertRaises(ProveedorNoHabilitado):
                        self.comprar(self.datos(forma_pago=forma_pago))
        self.assertFalse(Pedido.objects.exists())
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    def test_url_directa_get_y_post_no_permiten_comprar_a_suspendido(self):
        self.client.force_login(self.tecnico.usuario)
        cambiar_estado_perfil(perfil=self.proveedor, estado='suspendido')
        url = reverse('crear_pedido', args=[self.producto.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.datos()).status_code, 404)
        self.assertFalse(Pedido.objects.exists())

    def test_suspension_tras_cargar_formulario_se_revalida_al_comprar(self):
        self.client.force_login(self.tecnico.usuario)

        def suspender_y_comprar(**kwargs):
            cambiar_estado_perfil(perfil=self.proveedor, estado='suspendido')
            return crear_pedido(**kwargs)

        with patch('apps.pedidos.views.crear_pedido_servicio', side_effect=suspender_y_comprar):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                respuesta = self.client.post(reverse('crear_pedido', args=[self.producto.pk]), self.datos())
        self.assertContains(respuesta, 'no está habilitado')
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(callbacks, [])
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    def test_rehabilitar_restaura_busqueda_sin_perder_historial(self):
        pedido = self.comprar()
        cambiar_estado_perfil(perfil=self.proveedor, estado='suspendido')
        self.assertFalse(buscar_productos().exists())
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())
        cambiar_estado_perfil(perfil=self.proveedor, estado='aprobado')
        self.assertEqual(list(buscar_productos()), [self.producto])
        nuevo = self.comprar()
        self.assertNotEqual(pedido.pk, nuevo.pk)
