from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.models import Proveedor, Tecnico

from .exceptions import DeudaInexistente, SaldoInsuficiente
from .models import Credito, PagoCredito
from .services import (
    asignar_credito, reservar_saldo, resolver_pago, revocar_credito,
    saldar_deuda, solicitar_pago,
)


class CreditoServiceTests(TestCase):
    def setUp(self):
        tecnico_user = User.objects.create_user(username='credito-tec')
        proveedor_user = User.objects.create_user(username='credito-prov')
        self.tecnico = Tecnico.objects.create(
            usuario=tecnico_user, especialidad='mecanica_automotriz', ubicacion='CABA'
        )
        self.proveedor = Proveedor.objects.create(
            usuario=proveedor_user, nombre_negocio='Credito', direccion='CABA',
            rubro='mecanica_automotriz',
        )

    def test_reserva_permite_consumir_el_limite_exacto(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=1000
        )
        reservar_saldo(proveedor=self.proveedor, tecnico=self.tecnico, monto=1000)
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_disponible, 0)
        with self.assertRaises(SaldoInsuficiente):
            reservar_saldo(proveedor=self.proveedor, tecnico=self.tecnico, monto=1)

    def test_asignar_reactiva_y_revocar_desactiva(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=500, activo=False
        )
        asignado = asignar_credito(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=750
        )
        self.assertEqual(asignado.pk, credito.pk)
        self.assertTrue(asignado.activo)
        revocado = revocar_credito(credito=asignado)
        self.assertFalse(revocado.activo)

    def test_saldar_deuda_y_rechazar_repeticion(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=1000, saldo_usado=400
        )
        saldar_deuda(credito=credito)
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_usado, 0)
        with self.assertRaises(DeudaInexistente):
            saldar_deuda(credito=credito)

    def test_pago_pendiente_no_libera_hasta_confirmacion(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=1000, saldo_usado=400
        )
        pago = solicitar_pago(credito=credito)
        credito.refresh_from_db()
        self.assertEqual(credito.saldo_usado, 400)
        self.assertEqual(pago.estado, 'pendiente')
        resolver_pago(pago=pago, confirmado=True)
        credito.refresh_from_db()
        pago.refresh_from_db()
        self.assertEqual(credito.saldo_usado, 0)
        self.assertEqual(pago.estado, 'confirmado')

    def test_no_se_puede_generar_dos_solicitudes_pendientes(self):
        credito = Credito.objects.create(
            proveedor=self.proveedor, tecnico=self.tecnico, limite=1000, saldo_usado=400
        )
        solicitar_pago(credito=credito)
        with self.assertRaises(ValueError):
            solicitar_pago(credito=credito)
