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
