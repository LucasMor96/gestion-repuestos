import re

from django.core import mail
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


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
