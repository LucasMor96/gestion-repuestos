
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from apps.catalogo.models import Producto
from apps.creditos.models import Credito
from apps.pedidos.models import Pedido
from apps.usuarios.models import Proveedor, Tecnico
from apps.pedidos.exceptions import EstadoPedidoInvalido
from apps.pedidos.services import (
    aceptar_pedido,
    calcular_costo_envio,
    cancelar_pedido,
    cancelar_retiros_vencidos,
    rechazar_pedido,
)


class PedidoEmailTests(TestCase):
    def crear_tecnico(self, email='tecnico-pedido@example.com'):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Tec',
            last_name='Pedidos',
            is_active=True,
        )
        return Tecnico.objects.create(
            usuario=user,
            cuit=email[:13],
            especialidad='mecanica_automotriz',
            telefono='1122334455',
            ubicacion='CABA',
            estado='aprobado',
            is_approved=True,
        )

    def crear_proveedor(self, email='proveedor-pedido@example.com'):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Prov',
            last_name='Pedidos',
            is_active=True,
        )
        return Proveedor.objects.create(
            usuario=user,
            cuit=email[:13],
            nombre_negocio='Repuestos Pedido',
            direccion='Av. Test 123',
            rubro='mecanica_automotriz',
            estado='aprobado',
            is_approved=True,
        )

    def crear_producto(self, proveedor):
        return Producto.objects.create(
            proveedor=proveedor,
            nombre='Filtro de aceite',
            categoria='mecanica_automotriz',
            precio=1000,
            stock=5,
            disponible=True,
        )

    def crear_pedido(self, estado='pendiente'):
        tecnico = self.crear_tecnico()
        proveedor = self.crear_proveedor()
        producto = self.crear_producto(proveedor)
        pedido = Pedido.objects.create(
            tecnico=tecnico,
            proveedor=proveedor,
            producto=producto,
            cantidad=2,
            forma_entrega='retiro',
            estado=estado,
            monto_total=2000,
        )
        return pedido

    def test_crear_pedido_envia_email_al_proveedor(self):
        tecnico = self.crear_tecnico()
        proveedor = self.crear_proveedor()
        producto = self.crear_producto(proveedor)
        self.client.force_login(tecnico.usuario)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('crear_pedido', args=[producto.pk]),
                {
                    'clave_operacion': str(uuid4()),
                    'cantidad': 2,
                    'forma_entrega': 'retiro',
                    'forma_pago': 'mercadopago',
                    'notas': 'Lo retiro hoy',
                },
            )

        self.assertRedirects(response, reverse('mis_pedidos'))
        pedido = Pedido.objects.get(tecnico=tecnico, proveedor=proveedor, producto=producto)
        self.assertEqual(pedido.forma_pago, 'mercadopago')
        self.assertFalse(pedido.usa_credito)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [proveedor.usuario.email])
        self.assertIn('Nuevo pedido', mail.outbox[0].subject)
        self.assertIn(producto.nombre, mail.outbox[0].body)
        self.assertIn('MercadoPago (simulado)', mail.outbox[0].body)

    def test_crear_pedido_con_credito_comercial_usa_saldo(self):
        tecnico = self.crear_tecnico()
        proveedor = self.crear_proveedor()
        producto = self.crear_producto(proveedor)
        credito = Credito.objects.create(
            tecnico=tecnico,
            proveedor=proveedor,
            limite=5000,
            saldo_usado=0,
        )
        self.client.force_login(tecnico.usuario)

        response = self.client.post(
            reverse('crear_pedido', args=[producto.pk]),
            {
                'clave_operacion': str(uuid4()),
                'cantidad': 2,
                'forma_entrega': 'retiro',
                'forma_pago': 'credito_comercial',
                'notas': 'Uso credito',
            },
        )

        self.assertRedirects(response, reverse('mis_pedidos'))
        pedido = Pedido.objects.get(tecnico=tecnico, proveedor=proveedor, producto=producto)
        credito.refresh_from_db()
        self.assertEqual(pedido.forma_pago, 'credito_comercial')
        self.assertTrue(pedido.usa_credito)
        self.assertEqual(credito.saldo_usado, pedido.monto_total)

    def test_crear_pedido_por_transferencia_guarda_comprobante(self):
        tecnico = self.crear_tecnico()
        proveedor = self.crear_proveedor()
        producto = self.crear_producto(proveedor)
        comprobante = SimpleUploadedFile(
            'comprobante.pdf',
            b'%PDF-1.4 comprobante de prueba',
            content_type='application/pdf',
        )
        self.client.force_login(tecnico.usuario)

        response = self.client.post(
            reverse('crear_pedido', args=[producto.pk]),
            {
                'clave_operacion': str(uuid4()),
                'cantidad': 1,
                'forma_entrega': 'retiro',
                'forma_pago': 'transferencia',
                'comprobante_transferencia': comprobante,
                'notas': 'Transferido',
            },
        )

        self.assertRedirects(response, reverse('mis_pedidos'))
        pedido = Pedido.objects.get(tecnico=tecnico, proveedor=proveedor, producto=producto)
        self.assertEqual(pedido.forma_pago, 'transferencia')
        self.assertTrue(pedido.comprobante_transferencia.name.endswith('.pdf'))

    def test_proveedor_acepta_pedido_envia_email_al_tecnico(self):
        pedido = self.crear_pedido()
        self.client.force_login(pedido.proveedor.usuario)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('gestionar_pedido', args=[pedido.pk]),
                {
                    'accion': 'aceptar',
                    'respuesta': 'Listo para retirar',
                },
            )

        self.assertRedirects(response, reverse('pedidos_recibidos'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [pedido.tecnico.usuario.email])
        self.assertIn('Aceptado', mail.outbox[0].subject)
        self.assertIn('Listo para retirar', mail.outbox[0].body)

    def test_proveedor_rechaza_pedido_envia_email_al_tecnico(self):
        pedido = self.crear_pedido()
        self.client.force_login(pedido.proveedor.usuario)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('gestionar_pedido', args=[pedido.pk]),
                {
                    'accion': 'rechazar',
                    'respuesta': 'Sin stock por ahora',
                },
            )

        self.assertRedirects(response, reverse('pedidos_recibidos'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [pedido.tecnico.usuario.email])
        self.assertIn('Rechazado', mail.outbox[0].subject)
        self.assertIn('Sin stock por ahora', mail.outbox[0].body)

    def test_proveedor_propone_otro_producto_de_su_catalogo(self):
        pedido = self.crear_pedido()
        alternativa = Producto.objects.create(
            proveedor=pedido.proveedor,
            nombre='Filtro premium',
            modelo='FP-200',
            categoria='mecanica_automotriz',
            precio=1500,
            stock=pedido.cantidad,
            disponible=True,
        )
        self.client.force_login(pedido.proveedor.usuario)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('gestionar_pedido', args=[pedido.pk]),
                {
                    'accion': 'alternativa',
                    'producto_alternativo': alternativa.pk,
                    'respuesta': 'Es compatible con tu vehículo.',
                },
            )

        self.assertRedirects(response, reverse('pedidos_recibidos'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'rechazado')
        self.assertEqual(pedido.producto_alternativo, alternativa)
        self.assertIn('Es compatible con tu vehículo.', mail.outbox[0].body)
        self.assertIn('Filtro premium', mail.outbox[0].body)

        self.client.force_login(pedido.tecnico.usuario)
        historial = self.client.get(reverse('mis_pedidos'))
        self.assertContains(historial, 'Ver propuesta alternativa')
        self.assertContains(historial, reverse('crear_pedido', args=[alternativa.pk]))

    def test_proveedor_ve_cancelar_si_no_tiene_producto_alternativo(self):
        pedido = self.crear_pedido()
        self.client.force_login(pedido.proveedor.usuario)

        detalle = self.client.get(reverse('detalle_pedido_proveedor', args=[pedido.pk]))
        self.assertContains(detalle, 'Cancelar pedido')
        self.assertNotContains(detalle, 'Proponer alternativa')

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('gestionar_pedido', args=[pedido.pk]),
                {'accion': 'cancelar', 'respuesta': 'No hay reemplazo disponible.'},
            )

        self.assertRedirects(response, reverse('pedidos_recibidos'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'cancelado')
        self.assertIn('No hay reemplazo disponible.', mail.outbox[0].body)

    def test_completar_pedido_envia_email_a_tecnico_y_proveedor(self):
        pedido = self.crear_pedido(estado='aceptado')
        self.client.force_login(pedido.tecnico.usuario)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('completar_pedido', args=[pedido.pk]))

        self.assertRedirects(response, reverse('mis_pedidos'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [pedido.tecnico.usuario.email, pedido.proveedor.usuario.email],
        )
        self.assertIn('confirmado', mail.outbox[0].subject)
        self.assertIn('completado', mail.outbox[0].body)


class PedidoServiceTests(TestCase):
    def setUp(self):
        user_tecnico = User.objects.create_user(username='svc-tec', password='Password1!')
        user_proveedor = User.objects.create_user(username='svc-prov', password='Password1!')
        self.tecnico = Tecnico.objects.create(
            usuario=user_tecnico, especialidad='mecanica_automotriz', ubicacion='CABA',
            estado='aprobado', is_approved=True,
        )
        self.proveedor = Proveedor.objects.create(
            usuario=user_proveedor, nombre_negocio='Servicios', direccion='CABA',
            rubro='mecanica_automotriz', estado='aprobado', is_approved=True,
        )
        self.producto = Producto.objects.create(
            proveedor=self.proveedor, nombre='Filtro', categoria='mecanica_automotriz',
            precio=1000, stock=5,
        )

    def pedido(self, *, estado='pendiente', usa_credito=False):
        return Pedido.objects.create(
            tecnico=self.tecnico, proveedor=self.proveedor, producto=self.producto,
            cantidad=2, forma_entrega='retiro', forma_pago='credito_comercial' if usa_credito else 'mercadopago',
            estado=estado, monto_total=2000, usa_credito=usa_credito,
        )

    def test_calculo_envio_es_regla_de_dominio(self):
        self.assertEqual(calcular_costo_envio('retiro', 3), 0)
        self.assertEqual(calcular_costo_envio('envio', 3), 5300)

    def test_aceptar_descuenta_stock_y_rechaza_doble_transicion(self):
        pedido = self.pedido()
        aceptar_pedido(pedido=pedido)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)
        with self.assertRaises(EstadoPedidoInvalido):
            aceptar_pedido(pedido=pedido)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

    def test_cancelar_libera_credito(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=2000, saldo_usado=2000,
        )
        cancelar_pedido(pedido=self.pedido(usa_credito=True))
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_usado, 0)

    def test_rechazo_hace_rollback_si_falla_liberar_credito(self):
        pedido = self.pedido(usa_credito=True)
        with patch('apps.pedidos.services.liberar_saldo', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                rechazar_pedido(pedido=pedido)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')

    def test_retiro_vencido_restaura_stock(self):
        pedido = self.pedido(estado='aceptado')
        Pedido.objects.filter(pk=pedido.pk).update(
            fecha_actualizacion=timezone.now() - timedelta(hours=25)
        )
        self.assertEqual(cancelar_retiros_vencidos(Pedido.objects.filter(pk=pedido.pk)), 1)
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(pedido.estado, 'cancelado')
        self.assertEqual(self.producto.stock, 7)
