from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.models import Proveedor, Tecnico

from .exceptions import DeudaInexistente, SaldoInsuficiente
from .models import Credito
from .services import asignar_credito, reservar_saldo, revocar_credito, saldar_deuda


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
