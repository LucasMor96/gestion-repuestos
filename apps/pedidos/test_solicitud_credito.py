from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.creditos.exceptions import SaldoInsuficiente
from apps.creditos.models import Credito
from apps.creditos.services import saldar_deuda
from apps.usuarios.models import Proveedor

from .exceptions import EstadoPedidoInvalido, LimiteCreditoInvalido, StockInsuficiente
from .models import Pedido
from .services import aceptar_pedido, cancelar_pedido, cancelar_retiros_vencidos, rechazar_pedido
from .test_integridad import DatosPedidoMixin


class SolicitudCreditoTests(DatosPedidoMixin, TestCase):
    def solicitar(self, **datos):
        return self.comprar(self.datos(forma_pago='solicitud_credito', **datos))

    def test_solicitud_sin_credito_llega_al_proveedor_sin_deuda(self):
        self.credito.delete()
        self.client.force_login(self.tecnico.usuario)
        url = reverse('crear_pedido', args=[self.producto.pk])
        self.assertContains(self.client.get(url), 'Solicitud de crédito')
        datos = self.datos(forma_pago='solicitud_credito')
        with patch('apps.pedidos.notifications.send_mail') as enviar:
            with self.captureOnCommitCallbacks(execute=True):
                for _ in range(3):
                    self.assertRedirects(self.client.post(url, datos), reverse('mis_pedidos'))
            enviar.assert_called_once()
            self.assertIn('Solicitud de crédito', enviar.call_args.kwargs['subject'])
            self.assertEqual(enviar.call_args.kwargs['recipient_list'], [self.proveedor.usuario.email])
        pedido = Pedido.objects.get()
        self.assertFalse(pedido.usa_credito)
        self.assertEqual(pedido.estado, 'pendiente')
        self.assertFalse(Credito.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.client.force_login(self.proveedor.usuario)
        self.assertContains(self.client.get(reverse('pedidos_recibidos')), 'Solicitud de crédito')
        detalle = self.client.get(reverse('detalle_pedido_proveedor', args=[pedido.pk]))
        self.assertContains(detalle, 'Aprobar crédito y aceptar pedido')
        self.assertEqual(detalle.context['form']['limite_credito'].value(), Decimal('1000'))

    def test_aprobar_crea_cupo_reutilizable_y_descuenta_compra(self):
        self.credito.delete()
        pedido = self.solicitar()
        self.client.force_login(self.proveedor.usuario)
        with patch('apps.pedidos.notifications.send_mail') as enviar:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse('gestionar_pedido', args=[pedido.pk]), {
                    'accion': 'aceptar', 'limite_credito': '5000.00',
                })
            self.assertIn('solicitud de crédito fue aprobada', enviar.call_args.kwargs['message'])
        self.assertRedirects(response, reverse('pedidos_recibidos'))
        credito = Credito.objects.get()
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertTrue(credito.activo)
        self.assertEqual(credito.limite, 5000)
        self.assertEqual(credito.saldo_disponible, 4000)
        self.assertEqual(pedido.estado, 'aceptado')
        self.assertTrue(pedido.usa_credito)
        self.assertEqual(pedido.ciclo_credito, credito.ciclo)
        self.assertEqual(self.producto.stock, 9)
        self.comprar()
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_disponible, 3000)
        saldar_deuda(credito=credito)
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_disponible, 5000)

    def test_aprobar_reactiva_credito_sin_borrar_deuda_ni_ciclo(self):
        Credito.objects.filter(pk=self.credito.pk).update(activo=False, saldo_usado=500, ciclo=3)
        pedido = self.solicitar()
        aceptar_pedido(pedido=pedido, limite_credito=Decimal('2000'))
        self.credito.refresh_from_db()
        pedido.refresh_from_db()
        self.assertTrue(self.credito.activo)
        self.assertEqual(self.credito.saldo_usado, 1500)
        self.assertEqual(self.credito.limite, 2000)
        self.assertEqual(pedido.ciclo_credito, 3)

    def test_rechazar_o_cancelar_solicitud_no_toca_credito_existente(self):
        Credito.objects.filter(pk=self.credito.pk).update(saldo_usado=700, activo=False)
        rechazar_pedido(pedido=self.solicitar(), respuesta='No autorizado')
        cancelar_pedido(pedido=self.solicitar())
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 700)
        self.assertFalse(self.credito.activo)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_rechazo_notifica_y_no_exige_limite(self):
        self.credito.delete()
        pedido = self.solicitar()
        self.client.force_login(self.proveedor.usuario)
        with patch('apps.pedidos.notifications.send_mail') as enviar:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse('gestionar_pedido', args=[pedido.pk]), {
                    'accion': 'rechazar', 'limite_credito': 'invalido', 'respuesta': 'No autorizado',
                })
            self.assertIn('solicitud de crédito fue rechazada', enviar.call_args.kwargs['message'])
        self.assertRedirects(response, reverse('pedidos_recibidos'))
        self.assertFalse(Credito.objects.exists())

    def test_limite_insuficiente_revierte_otorgamiento_y_aceptacion(self):
        Credito.objects.filter(pk=self.credito.pk).update(saldo_usado=700, activo=False)
        pedido = self.solicitar()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(SaldoInsuficiente):
                aceptar_pedido(pedido=pedido, limite_credito=Decimal('1000'))
        self.assertEqual(callbacks, [])
        self.credito.refresh_from_db()
        pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(self.credito.limite, 10000)
        self.assertEqual(self.credito.saldo_usado, 700)
        self.assertFalse(self.credito.activo)
        self.assertEqual(pedido.estado, 'pendiente')
        self.assertFalse(pedido.usa_credito)
        self.assertEqual(self.producto.stock, 10)

    def test_error_de_limite_se_muestra_y_conserva_datos(self):
        pedido = self.solicitar()
        self.client.force_login(self.proveedor.usuario)
        url = reverse('gestionar_pedido', args=[pedido.pk])
        for limite in ('', '-1', '500', 'texto'):
            response = self.client.post(url, {
                'accion': 'aceptar', 'limite_credito': limite, 'respuesta': 'Mensaje conservado',
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('limite_credito', response.context['form'].errors)
            self.assertContains(response, 'Mensaje conservado')
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')

    def test_servicio_exige_limite_explicito(self):
        pedido = self.solicitar()
        with self.assertRaises(LimiteCreditoInvalido):
            aceptar_pedido(pedido=pedido)

    def test_sin_stock_no_habilita_credito(self):
        self.credito.delete()
        pedido = self.solicitar()
        self.producto.stock = 0
        self.producto.save(update_fields=['stock'])
        with self.assertRaises(StockInsuficiente):
            aceptar_pedido(pedido=pedido, limite_credito=Decimal('5000'))
        self.assertFalse(Credito.objects.exists())

    def test_otro_proveedor_no_puede_aprobar(self):
        pedido = self.solicitar()
        otro = Proveedor.objects.create(
            usuario=User.objects.create_user(username='otro-proveedor'),
            nombre_negocio='Otro', direccion='CABA', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        self.client.force_login(otro.usuario)
        response = self.client.post(reverse('gestionar_pedido', args=[pedido.pk]), {
            'accion': 'aceptar', 'limite_credito': 5000,
        })
        self.assertEqual(response.status_code, 404)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')

    def test_doble_aprobacion_no_duplica_deuda_ni_stock(self):
        pedido = self.solicitar()
        aceptar_pedido(pedido=pedido, limite_credito=Decimal('5000'))
        with self.assertRaises(EstadoPedidoInvalido):
            aceptar_pedido(pedido=pedido, limite_credito=Decimal('9000'))
        self.credito.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
        self.assertEqual(self.credito.limite, 5000)
        self.assertEqual(self.producto.stock, 9)

    def test_vencimiento_despues_de_saldar_respeta_deuda_nueva(self):
        pedido = self.solicitar()
        aceptar_pedido(pedido=pedido, limite_credito=Decimal('5000'))
        saldar_deuda(credito=self.credito)
        self.comprar()
        Pedido.objects.filter(pk=pedido.pk).update(fecha_actualizacion=timezone.now() - timedelta(hours=25))
        self.assertEqual(cancelar_retiros_vencidos([pedido]), 1)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
