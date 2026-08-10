
import re

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Proveedor, Tecnico


class LoginViewTests(TestCase):
    def test_authenticated_user_is_redirected_from_login_to_dashboard(self):
        user = User.objects.create_user(
            username='tecnico@example.com',
            email='tecnico@example.com',
            password='password123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('login'))

        self.assertRedirects(
            response,
            reverse('dashboard'),
            fetch_redirect_response=False,
        )

    def test_anonymous_user_can_view_login(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')
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

        self.assertRedirects(
            response,
            reverse('dashboard'),
            fetch_redirect_response=False,
        )

    def test_anonymous_user_can_view_registro(self):
        response = self.client.get(reverse('registro_tipo'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/registro_tipo.html')

    def test_registro_tecnico_guarda_coordenadas(self):
        response = self.client.post(reverse('registro_tecnico'), {
            'first_name': 'Mapa',
            'last_name': 'Tecnico',
            'email': 'mapa-tecnico@example.com',
            'cuit': '27-11111111-1',
            'especialidad': 'mecanica_automotriz',
            'telefono': '1122334455',
            'ubicacion': 'Rawson, Chubut',
            'latitud': '-43.3002',
            'longitud': '-65.1023',
            'password1': 'Testpass1234!',
            'password2': 'Testpass1234!',
        })

        self.assertRedirects(response, reverse('espera_aprobacion'))
        tecnico = Tecnico.objects.get(usuario__email='mapa-tecnico@example.com')
        self.assertEqual(tecnico.latitud, -43.3002)
        self.assertEqual(tecnico.longitud, -65.1023)

    def test_registro_proveedor_guarda_coordenadas(self):
        response = self.client.post(reverse('registro_proveedor'), {
            'first_name': 'Mapa',
            'last_name': 'Proveedor',
            'email': 'mapa-proveedor@example.com',
            'cuit': '30-22222222-2',
            'nombre_negocio': 'Mapa Repuestos',
            'direccion': 'Av Corrientes 1234, CABA',
            'latitud': '-34.6037',
            'longitud': '-58.3816',
            'rubro': 'mecanica_automotriz',
            'horario_desde': '9',
            'horario_hasta': '18',
            'password1': 'Testpass1234!',
            'password2': 'Testpass1234!',
        })

        self.assertRedirects(response, reverse('espera_aprobacion'))
        proveedor = Proveedor.objects.get(usuario__email='mapa-proveedor@example.com')
        self.assertEqual(proveedor.latitud, -34.6037)
        self.assertEqual(proveedor.longitud, -58.3816)

    def test_registro_tecnico_rechaza_contrasena_simple(self):
        response = self.client.post(reverse('registro_tecnico'), {
            'first_name': 'Clave',
            'last_name': 'Simple',
            'email': 'clave-simple-tecnico@example.com',
            'cuit': '27-33333333-3',
            'especialidad': 'mecanica_automotriz',
            'telefono': '1122334455',
            'ubicacion': 'Rawson, Chubut',
            'latitud': '-43.3002',
            'longitud': '-65.1023',
            'password1': 'password123',
            'password2': 'password123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'La contrasena debe incluir una letra mayuscula, un simbolo.',
            response.context['form'].errors['password2'],
        )
        self.assertFalse(User.objects.filter(email='clave-simple-tecnico@example.com').exists())

    def test_registro_tecnico_conserva_datos_si_falla(self):
        response = self.client.post(reverse('registro_tecnico'), {
            'first_name': 'Clave',
            'last_name': 'Simple',
            'email': 'conserva-tecnico@example.com',
            'cuit': '27-44444444-4',
            'especialidad': 'mecanica_automotriz',
            'telefono': '1122334455',
            'ubicacion': 'Rawson, Chubut',
            'latitud': '-43.3002',
            'longitud': '-65.1023',
            'password1': 'password123',
            'password2': 'password123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Clave"')
        self.assertContains(response, 'value="conserva-tecnico@example.com"')
        self.assertContains(response, 'value="27-44444444-4"')
        self.assertContains(response, 'value="Rawson, Chubut"')
        self.assertContains(response, 'value="password123"')

    def test_registro_proveedor_conserva_datos_si_falla(self):
        response = self.client.post(reverse('registro_proveedor'), {
            'first_name': 'Clave',
            'last_name': 'Proveedor',
            'email': 'conserva-proveedor@example.com',
            'cuit': '30-55555555-5',
            'nombre_negocio': 'Repuestos Conserva',
            'direccion': 'Av Corrientes 1234, CABA',
            'latitud': '-34.6037',
            'longitud': '-58.3816',
            'rubro': 'mecanica_automotriz',
            'horario_desde': '9',
            'horario_hasta': '18',
            'password1': 'password123',
            'password2': 'password123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Clave"')
        self.assertContains(response, 'value="conserva-proveedor@example.com"')
        self.assertContains(response, 'value="30-55555555-5"')
        self.assertContains(response, 'value="Repuestos Conserva"')
        self.assertContains(response, 'value="Av Corrientes 1234, CABA"')
        self.assertContains(response, 'value="9"')
        self.assertContains(response, 'value="18"')
        self.assertContains(response, 'value="password123"')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')

class PasswordResetTests(TestCase):
    def test_password_reset_pages_are_available(self):
        response = self.client.get(reverse('password_reset'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/password_reset_form.html')

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
                'new_password1': 'New-password123!',
                'new_password2': 'New-password123!',
            },
        )

        self.assertRedirects(response, reverse('password_reset_complete'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('New-password123!'))

    def test_password_reset_rechaza_contrasena_simple(self):
        user = User.objects.create_user(
            username='reset-simple@example.com',
            email='reset-simple@example.com',
            password='Password123!',
            is_active=True,
        )

        response = self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        reset_url = re.search(r'http://testserver(?P<path>/password-reset/\S+)', mail.outbox[0].body).group('path')
        response = self.client.get(reset_url, follow=True)
        reset_confirm_path = response.request['PATH_INFO']

        response = self.client.post(
            reset_confirm_path,
            {
                'new_password1': 'password123',
                'new_password2': 'password123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La contrasena debe incluir una letra mayuscula, un simbolo.')
        user.refresh_from_db()
        self.assertFalse(user.check_password('password123'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')

class LocationMapTests(TestCase):
    def crear_tecnico(self, email='map-tecnico@example.com', cuit='27-33333333-3'):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Tec',
            last_name='Mapa',
            is_active=True,
        )
        return Tecnico.objects.create(
            usuario=user,
            cuit=cuit,
            especialidad='mecanica_automotriz',
            telefono='1122334455',
            ubicacion='Rawson, Chubut',
            latitud=-43.3002,
            longitud=-65.1023,
            estado='aprobado',
            is_approved=True,
        )

    def crear_proveedor(self, email='map-proveedor@example.com', cuit='30-44444444-4'):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='password123',
            first_name='Prov',
            last_name='Mapa',
            is_active=True,
        )
        return Proveedor.objects.create(
            usuario=user,
            cuit=cuit,
            nombre_negocio='Mapa Repuestos',
            direccion='Av Corrientes 1234, CABA',
            rubro='mecanica_automotriz',
            latitud=-34.6037,
            longitud=-58.3816,
            estado='aprobado',
            is_approved=True,
        )

    def test_dashboard_muestra_mapa_del_perfil(self):
        tecnico = self.crear_tecnico()
        self.client.force_login(tecnico.usuario)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'data-static-map')
        self.assertContains(response, 'data-lat="-43.3002"')

    def test_perfiles_publicos_muestran_mapa(self):
        tecnico = self.crear_tecnico()
        proveedor = self.crear_proveedor()
        self.client.force_login(proveedor.usuario)

        response = self.client.get(reverse('perfil_tecnico', args=[tecnico.pk]))

        self.assertContains(response, 'data-static-map')
        self.assertContains(response, tecnico.ubicacion)

        self.client.force_login(tecnico.usuario)
        response = self.client.get(reverse('perfil_proveedor', args=[proveedor.pk]))

        self.assertContains(response, 'data-static-map')
        self.assertContains(response, proveedor.direccion)

    def test_editar_perfil_tecnico_guarda_coordenadas(self):
        tecnico = self.crear_tecnico()
        self.client.force_login(tecnico.usuario)

        response = self.client.post(reverse('editar_perfil'), {
            'first_name': 'Tec',
            'last_name': 'Mapa',
            'especialidad': 'mecanica_automotriz',
            'telefono': '1122334455',
            'ubicacion': 'Trelew, Chubut',
            'latitud': '-43.2489',
            'longitud': '-65.3051',
        })

        self.assertRedirects(response, reverse('dashboard'))
        tecnico.refresh_from_db()
        self.assertEqual(tecnico.ubicacion, 'Trelew, Chubut')
        self.assertEqual(tecnico.latitud, -43.2489)
        self.assertEqual(tecnico.longitud, -65.3051)

    def test_editar_perfil_proveedor_guarda_coordenadas(self):
        proveedor = self.crear_proveedor()
        self.client.force_login(proveedor.usuario)

        response = self.client.post(reverse('editar_perfil'), {
            'first_name': 'Prov',
            'last_name': 'Mapa',
            'nombre_negocio': 'Mapa Repuestos',
            'direccion': 'Av Siempre Viva 742, CABA',
            'latitud': '-34.6158',
            'longitud': '-58.4333',
            'rubro': 'mecanica_automotriz',
            'horario_desde': '9',
            'horario_hasta': '18',
        })

        self.assertRedirects(response, reverse('dashboard'))
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.direccion, 'Av Siempre Viva 742, CABA')
        self.assertEqual(proveedor.latitud, -34.6158)
        self.assertEqual(proveedor.longitud, -58.4333)
