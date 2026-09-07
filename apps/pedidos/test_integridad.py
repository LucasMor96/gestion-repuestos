from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.creditos.exceptions import SaldoInsuficiente
from apps.creditos.models import Credito
from apps.creditos.services import saldar_deuda
from apps.usuarios.models import Proveedor, Tecnico

from .models import Pedido
from .exceptions import EstadoPedidoInvalido
from .services import (
    aceptar_pedido, cancelar_pedido, cancelar_retiros_vencidos,
    crear_pedido, rechazar_pedido,
)


class DatosPedidoMixin:
    def setUp(self):
        super().setUp()
        self.tecnico = Tecnico.objects.create(
            usuario=User.objects.create_user(username='integridad-tecnico'),
            ubicacion='CABA', especialidad='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        self.proveedor = Proveedor.objects.create(
            usuario=User.objects.create_user(username='integridad-proveedor'),
            nombre_negocio='Repuestos', direccion='CABA', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        self.producto = Producto.objects.create(
            proveedor=self.proveedor, nombre='Filtro', categoria='mecanica_automotriz',
            precio=1000, stock=10,
        )
        self.credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=10000,
        )

    def datos(self, **cambios):
        return {
            'clave_operacion': uuid4(), 'cantidad': 1,
            'forma_entrega': 'retiro', 'forma_pago': 'credito_comercial',
            **cambios,
        }

    def comprar(self, datos=None):
        return crear_pedido(
            tecnico=self.tecnico, producto=self.producto,
            datos=self.datos() if datos is None else datos,
        )


class IntegridadPedidoTests(DatosPedidoMixin, TestCase):
    def test_migracion_separa_pedidos_anteriores_si_saldo_es_cero(self):
        anterior = self.comprar()
        # Simula la liquidacion anterior a la existencia de ciclos.
        Credito.objects.filter(pk=self.credito.pk).update(saldo_usado=0)
        migracion = import_module('apps.creditos.migrations.0002_credito_ciclo')
        with connection.schema_editor() as editor:
            migracion.separar_creditos_sin_deuda(apps, editor)
        nuevo = self.comprar()
        cancelar_pedido(pedido=anterior)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
        self.assertNotEqual(anterior.ciclo_credito, nuevo.ciclo_credito)

    def comprobar_cancelacion_saldada(self, accion):
        anterior = self.comprar(self.datos(cantidad=2))
        if accion == 'vencimiento':
            aceptar_pedido(pedido=anterior)
            Pedido.objects.filter(pk=anterior.pk).update(
                fecha_actualizacion=timezone.now() - timedelta(hours=25),
            )
        saldar_deuda(credito=self.credito)
        nuevo = self.comprar()
        if accion == 'vencimiento':
            self.assertEqual(cancelar_retiros_vencidos([anterior]), 1)
            self.producto.refresh_from_db()
            self.assertEqual(self.producto.stock, 10)
        elif accion == 'rechazo':
            rechazar_pedido(pedido=anterior)
        else:
            cancelar_pedido(pedido=anterior)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, Decimal('1000'))
        self.assertNotEqual(anterior.ciclo_credito, nuevo.ciclo_credito)
        cancelar_pedido(pedido=nuevo)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    def test_cancelar_pedido_saldado_conserva_deuda_nueva(self):
        self.comprobar_cancelacion_saldada('cancelacion')

    def test_rechazar_pedido_saldado_conserva_deuda_nueva(self):
        self.comprobar_cancelacion_saldada('rechazo')

    def test_vencer_pedido_saldado_conserva_deuda_nueva_y_restaura_stock(self):
        self.comprobar_cancelacion_saldada('vencimiento')

    def test_varias_saldaduras_no_reabren_deudas_anteriores(self):
        primero = self.comprar()
        saldar_deuda(credito=self.credito)
        segundo = self.comprar()
        saldar_deuda(credito=self.credito)
        self.comprar()
        cancelar_pedido(pedido=primero)
        rechazar_pedido(pedido=segundo)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
        self.assertEqual(self.credito.ciclo, 2)

    def test_reintento_no_reserva_ni_notifica_dos_veces(self):
        datos = self.datos()
        with patch('apps.pedidos.services.notificar_proveedor_nuevo_pedido') as notificar:
            with self.captureOnCommitCallbacks(execute=True):
                primero = self.comprar(datos)
                for _ in range(5):
                    self.assertEqual(self.comprar(datos).pk, primero.pk)
            notificar.assert_called_once()
        self.assertEqual(Pedido.objects.count(), 1)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_claves_distintas_permiten_compras_intencionales(self):
        self.assertNotEqual(self.comprar().pk, self.comprar().pk)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 2000)

    def test_base_de_datos_rechaza_clave_duplicada(self):
        pedido = self.comprar()
        pedido.pk = None
        with self.assertRaises(IntegrityError), transaction.atomic():
            pedido.save(force_insert=True)

    def test_fallo_no_consume_clave_y_permite_reintentar(self):
        datos = self.datos()
        Credito.objects.filter(pk=self.credito.pk).update(limite=500)
        with self.assertRaises(SaldoInsuficiente):
            self.comprar(datos)
        self.assertFalse(Pedido.objects.exists())
        Credito.objects.filter(pk=self.credito.pk).update(limite=10000)
        self.comprar(datos)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_reintento_tras_cancelacion_no_crea_otro_pedido(self):
        datos = self.datos()
        pedido = self.comprar(datos)
        cancelar_pedido(pedido=pedido)
        self.assertEqual(self.comprar(datos).estado, 'cancelado')
        self.assertEqual(Pedido.objects.count(), 1)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    def test_formulario_conserva_clave_tras_error_y_post_repetido(self):
        self.client.force_login(self.tecnico.usuario)
        url = reverse('crear_pedido', args=[self.producto.pk])
        respuesta = self.client.get(url)
        clave = str(respuesta.context['form']['clave_operacion'].value())
        self.assertContains(respuesta, 'name="clave_operacion"')
        datos = self.datos(clave_operacion=clave, cantidad=0)
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(str(respuesta.context['form']['clave_operacion'].value()), clave)
        self.assertFalse(Pedido.objects.exists())
        datos['cantidad'] = 1
        for _ in range(3):
            self.assertRedirects(self.client.post(url, datos), reverse('mis_pedidos'))
        self.assertEqual(Pedido.objects.count(), 1)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)

    def test_post_sin_clave_o_con_clave_invalida_no_compra(self):
        self.client.force_login(self.tecnico.usuario)
        url = reverse('crear_pedido', args=[self.producto.pk])
        for clave in ('', 'no-es-uuid'):
            respuesta = self.client.post(url, self.datos(clave_operacion=clave))
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn('clave_operacion', respuesta.context['form'].errors)
        self.assertFalse(Pedido.objects.exists())

    def test_transferencia_repetida_guarda_un_solo_comprobante(self):
        self.client.force_login(self.tecnico.usuario)
        url = reverse('crear_pedido', args=[self.producto.pk])
        datos = self.datos(forma_pago='transferencia')
        with TemporaryDirectory() as carpeta, self.settings(MEDIA_ROOT=carpeta):
            for _ in range(2):
                datos['comprobante_transferencia'] = SimpleUploadedFile(
                    'pago.pdf', b'%PDF-1.4 prueba', content_type='application/pdf',
                )
                self.assertRedirects(self.client.post(url, datos), reverse('mis_pedidos'))
            self.assertEqual(Pedido.objects.count(), 1)
            self.assertEqual(len(list(Path(carpeta).rglob('*.pdf'))), 1)


@skipUnlessDBFeature('has_select_for_update')
class ConcurrenciaPedidoTests(DatosPedidoMixin, TransactionTestCase):
    def ejecutar_juntos(self, *acciones):
        barrera = Barrier(len(acciones))

        def ejecutar(accion):
            close_old_connections()
            try:
                # Evita que un bloqueo defectuoso cuelgue indefinidamente la suite.
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                barrera.wait(timeout=5)
                return accion()
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=len(acciones)) as executor:
            tareas = [executor.submit(ejecutar, accion) for accion in acciones]
            return [tarea.result(timeout=15) for tarea in tareas]

    @patch('apps.pedidos.services.notificar_proveedor_nuevo_pedido')
    def test_compras_simultaneas_crean_un_solo_pedido(self, notificar):
        datos = self.datos()
        ids = self.ejecutar_juntos(
            lambda: self.comprar(datos).pk,
            lambda: self.comprar(datos).pk,
        )
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(Pedido.objects.count(), 1)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 1000)
        notificar.assert_called_once()

    @patch('apps.creditos.services.notificar_credito_asignado')
    @patch('apps.pedidos.services.notificar_tecnico_estado')
    @patch('apps.pedidos.services.notificar_proveedor_nuevo_pedido')
    def test_aprobaciones_simultaneas_otorgan_credito_una_vez(self, _nuevo, estado, asignado):
        self.credito.delete()
        pedido = self.comprar(self.datos(forma_pago='solicitud_credito'))

        def aprobar():
            try:
                aceptar_pedido(pedido=pedido, limite_credito=Decimal('5000'))
                return True
            except EstadoPedidoInvalido:
                return False

        resultados = self.ejecutar_juntos(aprobar, aprobar)
        self.assertEqual(sum(resultados), 1)
        credito = Credito.objects.get()
        self.assertEqual(credito.saldo_usado, 1000)
        self.assertEqual(credito.saldo_disponible, 4000)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 9)
        estado.assert_called_once()
        asignado.assert_called_once()

    @patch('apps.creditos.services.notificar_deuda_saldada')
    @patch('apps.pedidos.services.notificar_proveedor_nuevo_pedido')
    def test_saldar_y_comprar_simultaneamente_conservan_el_ciclo(self, *_mocks):
        self.comprar()
        _, nuevo = self.ejecutar_juntos(
            lambda: saldar_deuda(credito=self.credito),
            lambda: self.comprar(),
        )
        self.credito.refresh_from_db()
        esperado = 1000 if nuevo.ciclo_credito == self.credito.ciclo else 0
        self.assertEqual(self.credito.saldo_usado, esperado)
        cancelar_pedido(pedido=nuevo)
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)

    @patch('apps.creditos.services.notificar_deuda_saldada')
    @patch('apps.pedidos.services.notificar_proveedor_nuevo_pedido')
    def test_saldar_y_cancelar_simultaneamente_no_corrompen_saldo(self, *_mocks):
        anterior = self.comprar()
        self.comprar()
        self.ejecutar_juntos(
            lambda: saldar_deuda(credito=self.credito),
            lambda: cancelar_pedido(pedido=anterior),
        )
        self.credito.refresh_from_db()
        self.assertEqual(self.credito.saldo_usado, 0)
        self.assertEqual(self.credito.ciclo, 1)
