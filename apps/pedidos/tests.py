
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Producto
from creditos.models import Credito
from pedidos.models import Pedido
from usuarios.models import Proveedor, Tecnico


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

        response = self.client.post(
            reverse('crear_pedido', args=[producto.pk]),
            {
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

    def test_completar_pedido_envia_email_a_tecnico_y_proveedor(self):
        pedido = self.crear_pedido(estado='aceptado')
        self.client.force_login(pedido.tecnico.usuario)

        response = self.client.post(reverse('completar_pedido', args=[pedido.pk]))

        self.assertRedirects(response, reverse('mis_pedidos'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [pedido.tecnico.usuario.email, pedido.proveedor.usuario.email],
        )
        self.assertIn('confirmado', mail.outbox[0].subject)
        self.assertIn('completado', mail.outbox[0].body)
