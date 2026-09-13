from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalogo.models import Producto
from apps.pedidos.models import Pedido
from apps.usuarios.models import Proveedor, Tecnico
from apps.core.services import formatear_tiempo_respuesta


class DemoDataCommandTests(TestCase):
    @patch(
        'apps.core.management.commands.crear_usuarios_prueba.Command.obtener_imagen_producto',
        return_value='',
    )
    def test_crear_usuarios_prueba_crea_datos_en_una_base_vacia(self, _mock_image):
        output = StringIO()

        call_command('crear_usuarios_prueba', stdout=output)

        self.assertTrue(User.objects.filter(username='admin', is_staff=True).exists())
        self.assertTrue(Tecnico.objects.filter(usuario__username='tecnico_prueba').exists())
        self.assertTrue(Proveedor.objects.filter(usuario__username='proveedor_prueba').exists())
        self.assertTrue(Producto.objects.exists())
        self.assertTrue(Pedido.objects.exists())
        self.assertIn('Datos de prueba listos', output.getvalue())


class UrlCompatibilityTests(TestCase):
    def test_public_url_names_are_preserved(self):
        routes = {
            'inicio': [], 'registro_tipo': [], 'registro_tecnico': [],
            'registro_proveedor': [], 'login': [], 'logout': [],
            'password_reset': [], 'password_change': [],
            'password_change_done': [], 'espera_aprobacion': [],
            'dashboard': [], 'editar_perfil': [], 'buscar_repuestos': [],
            'catalogo_proveedor': [], 'agregar_producto': [], 'mis_pedidos': [],
            'exportar_historial': [], 'pedidos_recibidos': [], 'mis_creditos': [],
            'gestionar_creditos_proveedor': [], 'asignar_credito': [],
            'deudas_tecnicos': [], 'panel_moderacion': [],
            'perfil_tecnico': [1], 'perfil_proveedor': [1],
            'editar_producto': [1], 'eliminar_producto': [1],
            'toggle_disponibilidad': [1], 'crear_pedido': [1],
            'cancelar_pedido': [1], 'detalle_pedido_proveedor': [1],
            'gestionar_pedido': [1], 'completar_pedido': [1],
            'calificar_proveedor': [1], 'calificar_tecnico': [1],
            'revocar_credito': [1], 'detalle_deuda_tecnico': [1],
            'marcar_deuda_saldada': [1],
            'aprobar_usuario': ['tecnico', 1],
            'rechazar_usuario': ['tecnico', 1],
            'suspender_usuario': ['tecnico', 1],
            'solicitar_info': ['tecnico', 1],
        }

        for name, args in routes.items():
            with self.subTest(name=name):
                self.assertTrue(reverse(name, args=args).startswith('/'))


class DashboardRoutingTests(TestCase):
    def test_staff_dashboard_redirects_to_moderation(self):
        staff = User.objects.create_user(
            username='staff',
            password='Password1!',
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('panel_moderacion'))

    def test_user_without_business_profile_waits_for_approval(self):
        user = User.objects.create_user(
            username='sin_perfil',
            password='Password1!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('espera_aprobacion'))


class NotFoundPageTests(TestCase):
    def test_missing_page_uses_custom_404_template_in_debug(self):
        response = self.client.get('/dashh')

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')
        self.assertContains(response, 'No encontramos esta pagina', status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_missing_page_uses_custom_404_template(self):
        response = self.client.get('/ruta-que-no-existe/')

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')
        self.assertContains(response, 'No encontramos esta pagina', status_code=404)

class AuthorizationTests(TestCase):
    def crear_tecnico(self, email='tecnico@example.com', aprobado=True):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Tec',
            last_name='Test',
            is_active=aprobado,
        )
        return Tecnico.objects.create(
            usuario=user,
            cuit=email[:8],
            especialidad='mecanica_automotriz',
            ubicacion='CABA',
            estado='aprobado' if aprobado else 'pendiente',
            is_approved=aprobado,
        )

    def crear_proveedor(self, email='proveedor@example.com', aprobado=True):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Prov',
            last_name='Test',
            is_active=aprobado,
        )
        return Proveedor.objects.create(
            usuario=user,
            cuit=email[:8],
            nombre_negocio='Repuestos Test',
            direccion='Av. Siempre Viva 123',
            rubro='mecanica_automotriz',
            estado='aprobado' if aprobado else 'pendiente',
            is_approved=aprobado,
        )

    def test_proveedor_no_puede_entrar_a_busqueda_de_repuestos(self):
        proveedor = self.crear_proveedor()
        self.client.force_login(proveedor.usuario)

        response = self.client.get(reverse('buscar_repuestos'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_tecnico_no_puede_entrar_al_catalogo_de_proveedor(self):
        tecnico = self.crear_tecnico()
        self.client.force_login(tecnico.usuario)

        response = self.client.get(reverse('catalogo_proveedor'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_acciones_de_catalogo_no_se_ejecutan_por_get(self):
        proveedor = self.crear_proveedor()
        producto = Producto.objects.create(
            proveedor=proveedor,
            nombre='Filtro',
            categoria='mecanica_automotriz',
            precio=100,
            stock=5,
            disponible=True,
        )
        self.client.force_login(proveedor.usuario)

        response = self.client.get(reverse('toggle_disponibilidad', args=[producto.pk]))

        producto.refresh_from_db()
        self.assertEqual(response.status_code, 405)
        self.assertTrue(producto.disponible)

    def test_aprobar_usuario_requiere_post(self):
        staff = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='password123',
            is_staff=True,
        )
        tecnico = self.crear_tecnico(email='pendiente@example.com', aprobado=False)
        self.client.force_login(staff)

        response = self.client.get(reverse('aprobar_usuario', args=['tecnico', tecnico.pk]))

        tecnico.refresh_from_db()
        tecnico.usuario.refresh_from_db()
        self.assertEqual(response.status_code, 405)
        self.assertFalse(tecnico.is_approved)
        self.assertFalse(tecnico.usuario.is_active)

    def test_tipo_de_moderacion_invalido_devuelve_404(self):
        staff = User.objects.create_user(
            username='admin2@example.com',
            email='admin2@example.com',
            password='password123',
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.post(reverse('aprobar_usuario', args=['cliente', 1]))

        self.assertEqual(response.status_code, 404)


class DashboardServiceTests(TestCase):
    def test_formatea_los_distintos_rangos_de_respuesta(self):
        self.assertEqual(formatear_tiempo_respuesta(None), 'Sin respuestas')
        self.assertEqual(formatear_tiempo_respuesta(120), '2 min')
        self.assertEqual(formatear_tiempo_respuesta(7200), '2.0 h')
