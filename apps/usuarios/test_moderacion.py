from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.test import Client, TestCase
from django.urls import reverse

from .forms import RespuestaModeracionForm
from .models import ImagenModeracion, Proveedor, RespuestaModeracion, Tecnico
from .services import cambiar_estado_perfil


def foto():
    contenido = BytesIO()
    Image.new('RGB', (10, 10)).save(contenido, format='PNG')
    return SimpleUploadedFile('foto.png', contenido.getvalue(), content_type='image/png')


class ModeracionInformacionTests(TestCase):
    def setUp(self):
        self.directorio = TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)
        self.almacenamiento = patch.object(ImagenModeracion._meta.get_field('imagen'), 'storage',
                                          FileSystemStorage(location=self.directorio.name))
        self.almacenamiento.start()
        self.addCleanup(self.almacenamiento.stop)
        self.usuario = User.objects.create_user('pendiente', email='pendiente@example.com',
                                               password='Test123!', is_active=False)
        self.perfil = Tecnico.objects.create(usuario=self.usuario, especialidad='mecanica_automotriz',
                                             ubicacion='CABA', nota_admin='Adjuntá documentación')
        self.staff = User.objects.create_user('admin', is_staff=True)

    def ingresar(self):
        return self.client.post(reverse('login'), {'email': self.usuario.email, 'password': 'Test123!'}, follow=True)

    def test_pedir_info_conserva_estado_y_muestra_solicitud(self):
        admin = Client()
        admin.force_login(self.staff)
        admin.post(reverse('solicitar_info', args=['tecnico', self.perfil.pk]), {'nota': 'Foto del certificado'})
        self.perfil.refresh_from_db()
        self.usuario.refresh_from_db()
        self.assertEqual(self.perfil.estado, 'pendiente')
        self.assertFalse(self.usuario.is_active)
        response = self.ingresar()
        self.assertContains(response, 'Información adicional solicitada')
        self.assertContains(response, 'Foto del certificado')
        self.assertNotContains(response, 'Cuenta suspendida')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_envia_varias_imagenes_y_admin_las_ve(self):
        self.ingresar()
        response = self.client.post(reverse('espera_aprobacion'), {
            'texto': 'Estos son mis documentos', 'imagenes': [foto(), foto()]}, follow=True)
        self.assertContains(response, 'Información enviada')
        self.assertEqual(ImagenModeracion.objects.count(), 2)
        self.assertEqual(RespuestaModeracion.objects.get().solicitud, self.perfil.nota_admin)
        imagen = ImagenModeracion.objects.first()
        url = reverse('imagen_moderacion', args=[imagen.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content))
        admin = Client()
        admin.force_login(self.staff)
        panel = admin.get(reverse('panel_moderacion'))
        self.assertContains(panel, 'Estos son mis documentos')
        self.assertContains(panel, url)
        response = admin.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content))

    def test_proveedor_puede_responder_solo_con_imagen(self):
        self.perfil.delete()
        Proveedor.objects.create(usuario=self.usuario, nombre_negocio='Local', direccion='CABA',
                                 rubro='mecanica_automotriz', nota_admin='Habilitación')
        self.ingresar()
        self.client.post(reverse('espera_aprobacion'), {'imagenes': [foto()]})
        self.assertEqual(ImagenModeracion.objects.count(), 1)

    def test_pendiente_sin_nota_no_muestra_suspension(self):
        self.perfil.nota_admin = ''
        self.perfil.save()
        response = self.ingresar()
        self.assertContains(response, 'Cuenta pendiente de aprobación')
        self.assertNotContains(response, 'Cuenta suspendida')
        self.client.post(reverse('espera_aprobacion'), {'texto': 'No solicitado'})
        self.assertFalse(RespuestaModeracion.objects.exists())

    def test_suspendido_y_rechazado_no_pueden_responder(self):
        for estado, titulo in [('suspendido', 'Cuenta suspendida'), ('rechazado', 'Solicitud rechazada')]:
            cambiar_estado_perfil(perfil=self.perfil, estado=estado, nota='Motivo')
            self.assertContains(self.ingresar(), titulo)
            self.client.post(reverse('espera_aprobacion'), {'texto': 'Respuesta'})
            self.assertFalse(RespuestaModeracion.objects.exists())

    def test_anonimo_otro_usuario_y_clave_incorrecta_no_acceden(self):
        self.ingresar()
        self.client.post(reverse('espera_aprobacion'), {'imagenes': [foto()]})
        url = reverse('imagen_moderacion', args=[ImagenModeracion.objects.get().pk])
        otro = Client()
        self.assertEqual(otro.get(url).status_code, 404)
        otro.force_login(User.objects.create_user('otro'))
        self.assertEqual(otro.get(url).status_code, 404)
        self.client.post(reverse('login'), {'email': self.usuario.email, 'password': 'incorrecta'})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.post(reverse('espera_aprobacion'), {'texto': 'Sin acceso'})
        self.assertEqual(RespuestaModeracion.objects.count(), 1)

    def test_aprobacion_o_cambio_clave_revoca_envio(self):
        self.ingresar()
        self.usuario.set_password('Otra123!')
        self.usuario.save()
        self.client.post(reverse('espera_aprobacion'), {'texto': 'Sin acceso'})
        self.assertFalse(RespuestaModeracion.objects.exists())
        self.usuario.set_password('Test123!')
        self.usuario.save()
        self.ingresar()
        cambiar_estado_perfil(perfil=self.perfil, estado='aprobado')
        self.client.post(reverse('espera_aprobacion'), {'texto': 'Aprobado'})
        self.assertFalse(RespuestaModeracion.objects.exists())

    def test_archivo_invalido_no_guarda_respuesta_parcial(self):
        self.ingresar()
        response = self.client.post(reverse('espera_aprobacion'), {
            'texto': 'Documentos', 'imagenes': [foto(), SimpleUploadedFile('falsa.png', b'no es una imagen')]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(RespuestaModeracion.objects.exists())

    def test_valida_cantidad_tamano_y_respuesta_vacia(self):
        self.assertFalse(RespuestaModeracionForm({}).is_valid())
        self.assertFalse(RespuestaModeracionForm({}, {'imagenes': [foto() for _ in range(6)]}).is_valid())
        grande = foto()
        grande.size = 5 * 1024 * 1024 + 1
        self.assertFalse(RespuestaModeracionForm({}, {'imagenes': [grande]}).is_valid())
        self.assertTrue(RespuestaModeracionForm({'texto': 'Respuesta sin imágenes'}).is_valid())
