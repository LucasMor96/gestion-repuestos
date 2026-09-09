from django.test import TestCase
from django.urls import reverse

from .exceptions import FormaPagoInvalida
from .forms import PedidoForm
from .models import Pedido
from .test_integridad import DatosPedidoMixin


class FormasPagoTests(DatosPedidoMixin, TestCase):
    def test_solo_se_ofrecen_las_tres_formas_vigentes(self):
        opciones = {valor for valor, _ in PedidoForm().fields['forma_pago'].choices}
        self.assertEqual(opciones, {'transferencia', 'credito_comercial', 'solicitud_credito'})
        self.client.force_login(self.tecnico.usuario)
        respuesta = self.client.get(reverse('crear_pedido', args=[self.producto.pk]))
        self.assertNotContains(respuesta, 'mercadopago')

    def test_post_manipulado_no_crea_pedido(self):
        self.client.force_login(self.tecnico.usuario)
        respuesta = self.client.post(reverse('crear_pedido', args=[self.producto.pk]),
                                     self.datos(forma_pago='mercadopago'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('forma_pago', respuesta.context['form'].errors)
        self.assertFalse(Pedido.objects.exists())

    def test_servicio_tambien_rechaza_forma_retirada(self):
        with self.assertRaises(FormaPagoInvalida):
            self.comprar(self.datos(forma_pago='mercadopago'))
        self.assertFalse(Pedido.objects.exists())

    def test_pedido_historico_conserva_datos_y_etiqueta_legible(self):
        pedido = self.comprar()
        Pedido.objects.filter(pk=pedido.pk).update(forma_pago='mercadopago')
        pedido.refresh_from_db()
        self.assertEqual(pedido.forma_pago, 'mercadopago')
        self.assertEqual(pedido.get_forma_pago_display(), 'Medio de pago retirado (histórico)')
