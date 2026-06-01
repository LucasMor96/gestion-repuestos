import re

from django.core import mail
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Producto, Proveedor, Tecnico


class LoginViewTests(TestCase):
    def test_authenticated_user_is_redirected_from_login_to_dashboard(self):
        user = User.objects.create_user(
            username='tecnico@example.com',
            email='tecnico@example.com',
            password='password123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('login'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_anonymous_user_can_view_login(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'plataforma/login.html')
        self.assertContains(response, reverse('password_reset'))


class RegistroViewTests(TestCase):
    def test_authenticated_user_is_redirected_from_registro_to_dashboard(self):
        user = User.objects.create_user(
            username='tecnico@example.com',
            email='tecnico@example.com',
            password='password123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('registro_tipo'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_anonymous_user_can_view_registro(self):
        response = self.client.get(reverse('registro_tipo'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'plataforma/registro_tipo.html')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def test_password_reset_pages_are_available(self):
        response = self.client.get(reverse('password_reset'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'plataforma/password_reset_form.html')

    def test_user_can_reset_password_from_email_link(self):
        user = User.objects.create_user(
            username='tecnico@example.com',
            email='tecnico@example.com',
            password='password123',
            is_active=True,
        )

        response = self.client.post(
            reverse('password_reset'),
            {'email': user.email},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Restablecer contrasena en LUMA', mail.outbox[0].subject)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')
        self.assertIn('Crear nueva contrasena', mail.outbox[0].alternatives[0][0])

        reset_url = re.search(r'http://testserver(?P<path>/password-reset/\S+)', mail.outbox[0].body).group('path')
        response = self.client.get(reset_url, follow=True)
        reset_confirm_path = response.request['PATH_INFO']

        response = self.client.post(
            reset_confirm_path,
            {
                'new_password1': 'new-password123',
                'new_password2': 'new-password123',
            },
        )

        self.assertRedirects(response, reverse('password_reset_complete'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('new-password123'))


class NotFoundPageTests(TestCase):
    def test_missing_page_uses_custom_404_template_in_debug(self):
        response = self.client.get('/dashh')

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, 'No encontramos esta pagina', status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_missing_page_uses_custom_404_template(self):
        response = self.client.get('/ruta-que-no-existe/')

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
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
