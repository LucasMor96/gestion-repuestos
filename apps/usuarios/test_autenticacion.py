from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .forms import RegistroProveedorForm, RegistroTecnicoForm
from .models import Proveedor, Tecnico
from .services import autenticar_por_email


def datos_registro(tipo, email='nuevo@example.com'):
    datos = {
        'first_name': 'Ana', 'last_name': 'Perez', 'email': email,
        'cuit': '27-12345678-0',
        'password1': 'ClaveSegura42!', 'password2': 'ClaveSegura42!',
    }
    if tipo == 'tecnico':
        datos.update(especialidad='tecnico_computadoras', ubicacion='Cordoba')
    else:
        datos.update(nombre_negocio='Repuestos Ana', direccion='Cordoba',
                     rubro='tecnico_computadoras', horario_desde='9', horario_hasta='18')
    return datos


FORMULARIOS = (
    ('tecnico', RegistroTecnicoForm, Tecnico),
    ('proveedor', RegistroProveedorForm, Proveedor),
)


class RegistroSeguroTests(TestCase):
    def test_falla_del_perfil_revierte_usuario_para_ambos_roles(self):
        for tipo, formulario, modelo in FORMULARIOS:
            with self.subTest(tipo=tipo):
                email = f'{tipo}@example.com'
                form = formulario(datos_registro(tipo, email))
                self.assertTrue(form.is_valid(), form.errors)
                with patch.object(modelo.objects, 'create', side_effect=RuntimeError('Fallo del perfil')):
                    with self.assertRaises(RuntimeError):
                        form.save()
                self.assertFalse(User.objects.filter(email=email).exists())
                self.assertFalse(modelo.objects.exists())

    def test_registro_normaliza_email_y_deja_cuenta_pendiente(self):
        for tipo, _, modelo in FORMULARIOS:
            with self.subTest(tipo=tipo):
                response = self.client.post(reverse(f'registro_{tipo}'),
                                            datos_registro(tipo, f'  {tipo.upper()}@Example.COM  '))
                self.assertRedirects(response, reverse('espera_aprobacion'))
                perfil = modelo.objects.get(usuario__email=f'{tipo}@example.com')
                self.assertEqual(perfil.usuario.username, f'{tipo}@example.com')
                self.assertTrue(perfil.usuario.check_password('ClaveSegura42!'))
                self.assertFalse(perfil.usuario.is_active)
                self.assertFalse(perfil.is_approved)
                self.assertEqual(perfil.estado, 'pendiente')
                self.assertNotIn('_auth_user_id', self.client.session)

    def test_rechaza_email_existente_con_otras_mayusculas_o_espacios(self):
        User.objects.create_user('legacy', email=' Ana@Example.COM ')
        for tipo, formulario, _ in FORMULARIOS:
            with self.subTest(tipo=tipo):
                form = formulario(datos_registro(tipo, 'ana@example.com'))
                self.assertFalse(form.is_valid())
                self.assertIn('email', form.errors)

    def test_rechaza_email_que_no_cabe_en_username(self):
        email = 'a' * 64 + '@' + 'b' * 60 + '.' + 'c' * 30 + '.com'
        for tipo, formulario, _ in FORMULARIOS:
            with self.subTest(tipo=tipo):
                form = formulario(datos_registro(tipo, email))
                self.assertFalse(form.is_valid())
                self.assertIn('email', form.errors)

    def test_conflicto_email_despues_de_validar_muestra_error_sin_cuenta_parcial(self):
        for tipo, formulario, modelo in FORMULARIOS:
            with self.subTest(tipo=tipo):
                email = f'carrera-{tipo}@example.com'
                validar = formulario.is_valid

                def validar_y_registrar_otro(form):
                    valido = validar(form)
                    if valido:
                        User.objects.create_user(f'competidor-{tipo}', email=email.upper())
                    return valido

                with patch.object(formulario, 'is_valid', validar_y_registrar_otro):
                    response = self.client.post(reverse(f'registro_{tipo}'), datos_registro(tipo, email))
                self.assertEqual(response.status_code, 200)
                self.assertIn('email', response.context['form'].errors)
                self.assertFalse(User.objects.filter(username=email).exists())
                self.assertFalse(modelo.objects.exists())
                self.assertNotContains(response, 'ClaveSegura42!')

    def test_conflicto_cuit_despues_de_validar_revierte_usuario_y_muestra_error(self):
        for tipo, formulario, modelo in FORMULARIOS:
            with self.subTest(tipo=tipo):
                email = f'cuit-{tipo}@example.com'
                validar = formulario.is_valid

                def validar_y_registrar_otro(form):
                    valido = validar(form)
                    if valido:
                        usuario = User.objects.create_user(f'competidor-cuit-{tipo}')
                        campos = {'especialidad': 'tecnico_computadoras', 'ubicacion': 'Cordoba'} if tipo == 'tecnico' else {
                            'nombre_negocio': 'Otro', 'direccion': 'Cordoba', 'rubro': 'tecnico_computadoras',
                        }
                        modelo.objects.create(usuario=usuario, cuit=form.cleaned_data['cuit'], **campos)
                    return valido

                with patch.object(formulario, 'is_valid', validar_y_registrar_otro):
                    response = self.client.post(reverse(f'registro_{tipo}'), datos_registro(tipo, email))
                self.assertEqual(response.status_code, 200)
                self.assertIn('cuit', response.context['form'].errors)
                self.assertFalse(User.objects.filter(email=email).exists())
                self.assertEqual(modelo.objects.count(), 1)


class UnicidadEmailTests(TestCase):
    def test_base_impide_emails_equivalentes_incluso_fuera_del_formulario(self):
        User.objects.create_user('original', email='ana@example.com')
        for email in ('ana@example.com', 'ANA@EXAMPLE.COM', ' ana@example.com '):
            with self.subTest(email=email):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    User.objects.create_user('duplicado', email=email)
                self.assertEqual(User.objects.count(), 1)

    def test_permite_varias_cuentas_sin_email_pero_no_login_por_email_vacio(self):
        User.objects.create_user('sin-email-1', password='ClaveSegura42!')
        User.objects.create_user('sin-email-2', password='ClaveSegura42!')
        resultado = autenticar_por_email(email='', password='ClaveSegura42!')
        self.assertEqual(resultado.estado, 'credenciales_invalidas')
        self.assertIsNone(resultado.usuario)


class LoginSeguroTests(TestCase):
    def crear_perfil(self, tipo, *, activo=True, estado='aprobado', aprobado=True):
        usuario = User.objects.create_user(
            f'legacy-{tipo}', email=f'{tipo}@example.com', password='ClaveSegura42!', is_active=activo,
        )
        campos = {'especialidad': 'tecnico_computadoras', 'ubicacion': 'Cordoba'} if tipo == 'tecnico' else {
            'nombre_negocio': 'Local', 'direccion': 'Cordoba', 'rubro': 'tecnico_computadoras',
        }
        modelo = Tecnico if tipo == 'tecnico' else Proveedor
        return modelo.objects.create(usuario=usuario, estado=estado, is_approved=aprobado, **campos)

    def test_login_normalizado_aprobado_funciona_para_ambos_roles(self):
        for tipo in ('tecnico', 'proveedor'):
            with self.subTest(tipo=tipo):
                perfil = self.crear_perfil(tipo)
                cliente = Client()
                response = cliente.post(reverse('login'), {
                    'email': f' {tipo.upper()}@Example.COM ', 'password': 'ClaveSegura42!',
                })
                self.assertRedirects(response, reverse('dashboard'))
                self.assertEqual(int(cliente.session['_auth_user_id']), perfil.usuario_id)
                self.assertNotIn('acceso_moderacion', cliente.session)

    def test_estados_inconsistentes_no_crean_sesion_comercial(self):
        casos = (
            (True, 'pendiente', False), (True, 'rechazado', False),
            (True, 'suspendido', False), (True, 'aprobado', False),
            (False, 'aprobado', True), (True, 'pendiente', True),
        )
        for tipo in ('tecnico', 'proveedor'):
            for activo, estado, aprobado in casos:
                with self.subTest(tipo=tipo, activo=activo, estado=estado, aprobado=aprobado):
                    perfil = self.crear_perfil(tipo, activo=activo, estado=estado, aprobado=aprobado)
                    cliente = Client()
                    response = cliente.post(reverse('login'), {
                        'email': perfil.usuario.email, 'password': 'ClaveSegura42!',
                    }, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn('_auth_user_id', cliente.session)
                    self.assertIn('acceso_moderacion', cliente.session)
                    self.assertNotContains(response, '<h2 class="fw-bold">Cuenta aprobada</h2>')
                    self.assertRedirects(cliente.get(reverse('dashboard')), reverse('login') + '?next=/dashboard/')
                    perfil.usuario.delete()

    def test_staff_activo_puede_ingresar_sin_perfil(self):
        usuario = User.objects.create_user('staff-login', email='staff@example.com',
                                           password='ClaveSegura42!', is_staff=True)
        response = self.client.post(reverse('login'), {
            'email': usuario.email, 'password': 'ClaveSegura42!',
        })
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('panel_moderacion'))
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    def test_staff_inactivo_no_puede_ingresar(self):
        usuario = User.objects.create_user('staff-inactivo', email='staff@example.com',
                                           password='ClaveSegura42!', is_staff=True, is_active=False)
        self.client.post(reverse('login'), {'email': usuario.email, 'password': 'ClaveSegura42!'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_activo_sin_perfil_no_puede_ingresar(self):
        usuario = User.objects.create_user('sin-perfil', email='sin-perfil@example.com', password='ClaveSegura42!')
        self.client.post(reverse('login'), {'email': usuario.email, 'password': 'ClaveSegura42!'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_clave_incorrecta_no_otorga_acceso_limitado_ni_comercial(self):
        perfil = self.crear_perfil('tecnico', activo=False, estado='pendiente', aprobado=False)
        response = self.client.post(reverse('login'), {'email': perfil.usuario.email, 'password': 'incorrecta'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertNotIn('acceso_moderacion', self.client.session)


class LogoutSeguroTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('logout-user', password='ClaveSegura42!')
        self.cliente = Client(enforce_csrf_checks=True)
        self.cliente.force_login(self.usuario)

    def test_get_no_cierra_sesion(self):
        self.assertEqual(self.cliente.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.cliente.session)

    def test_post_sin_csrf_no_cierra_sesion(self):
        self.assertEqual(self.cliente.post(reverse('logout')).status_code, 403)
        self.assertIn('_auth_user_id', self.cliente.session)

    def test_boton_envia_post_y_csrf_y_cierra_sesion(self):
        response = self.cliente.get(reverse('espera_aprobacion'))
        self.assertContains(response, f'<form method="post" action="{reverse("logout")}"')
        csrf = self.cliente.cookies['csrftoken'].value
        response = self.cliente.post(reverse('logout'), {'csrfmiddlewaretoken': csrf})
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.cliente.session)

    def test_logout_tambien_revoca_acceso_limitado(self):
        sesion = self.client.session
        sesion['acceso_moderacion'] = 'acceso-anterior'
        sesion.save()
        self.client.post(reverse('logout'))
        self.assertNotIn('acceso_moderacion', self.client.session)


class MigracionEmailTests(TransactionTestCase):
    anterior = [('usuarios', '0002_respuestamoderacion_imagenmoderacion')]
    actual = [('usuarios', '0003_email_unico_normalizado')]

    def setUp(self):
        MigrationExecutor(connection).migrate(self.anterior)

    def tearDown(self):
        # Restablece el esquema incluso despues de probar un conflicto de datos.
        User.objects.filter(username='migration-duplicate').delete()
        MigrationExecutor(connection).migrate(self.actual)
        super().tearDown()

    def test_normaliza_email_sin_cambiar_username_id_o_relaciones(self):
        usuario = User.objects.create_user('NombreHistorico', email=' Legacy@Example.COM ')
        User.objects.filter(pk=usuario.pk).update(email=' Legacy@Example.COM ')
        perfil = Tecnico.objects.create(usuario=usuario, especialidad='tecnico_computadoras', ubicacion='Cordoba')
        MigrationExecutor(connection).migrate(self.actual)
        usuario.refresh_from_db()
        perfil.refresh_from_db()
        self.assertEqual(usuario.email, 'legacy@example.com')
        self.assertEqual(usuario.username, 'NombreHistorico')
        self.assertEqual(perfil.usuario_id, usuario.pk)

    def test_duplicados_detienen_migracion_sin_modificar_o_eliminar_cuentas(self):
        original = User.objects.create_user('migration-original', email='Ana@Example.COM', password='ClaveSegura42!')
        duplicado = User.objects.create_user('migration-duplicate', email=' ana@example.com ', password='ClaveSegura42!')
        # create_user() normaliza el dominio; simula los valores historicos exactos.
        User.objects.filter(pk=original.pk).update(email='Ana@Example.COM')
        User.objects.filter(pk=duplicado.pk).update(email=' ana@example.com ')
        # El servicio rechaza un email ambiguo incluso antes de instalar el indice.
        resultado = autenticar_por_email(email='ana@example.com', password='ClaveSegura42!')
        self.assertEqual(resultado.estado, 'credenciales_invalidas')
        self.assertIsNone(resultado.usuario)
        with self.assertRaisesMessage(RuntimeError, 'Hay cuentas con el mismo email'):
            MigrationExecutor(connection).migrate(self.actual)
        original.refresh_from_db()
        duplicado.refresh_from_db()
        self.assertEqual(original.email, 'Ana@Example.COM')
        self.assertEqual(duplicado.email, ' ana@example.com ')
