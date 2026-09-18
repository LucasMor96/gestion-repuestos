from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Proveedor, Tecnico

from .models import Producto


class CatalogoPublicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.proveedor = Proveedor.objects.create(
            usuario=User.objects.create_user(username='proveedor-publico'),
            nombre_negocio='Proveedor reservado', direccion='Dirección reservada 456',
            horarios='Horario reservado', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        cls.producto = Producto.objects.create(
            proveedor=cls.proveedor, nombre='Filtro premium', modelo='Modelo interno X1',
            descripcion='Descripción reservada', imagen='productos/reservada.jpg',
            categoria='mecanica_automotriz', precio=1500, stock=7,
        )
        cls.tecnico = Tecnico.objects.create(
            usuario=User.objects.create_user(username='tecnico-publico'),
            especialidad='mecanica_automotriz', ubicacion='CABA',
            estado='aprobado', is_approved=True,
        )

    def test_inicio_conserva_portada_y_agrega_acceso_al_catalogo(self):
        response = self.client.get(reverse('inicio'))
        self.assertTemplateUsed(response, 'core/inicio.html')
        self.assertContains(response, 'La confianza del taller,')
        self.assertContains(response, 'Ver catálogo')
        self.assertContains(response, f'href="{reverse("buscar_repuestos")}"')

    def test_visitante_solo_ve_datos_publicos_del_repuesto(self):
        response = self.client.get(reverse('buscar_repuestos'))
        for texto in ('Filtro premium', self.producto.get_categoria_display(),
                      'Precio de referencia', '$ 1.500', 'Ver proveedor',
                      f'src="{self.producto.imagen.url}"'):
            self.assertContains(response, texto)
        for texto in (self.proveedor.nombre_negocio, self.proveedor.direccion,
                      self.proveedor.horarios, self.producto.modelo,
                      self.producto.descripcion,
                      'Stock:', 'Solicitar', 'Ver Crédito',
                      reverse('crear_pedido', args=[self.producto.pk]),
                      reverse('mis_creditos')):
            self.assertNotContains(response, texto)

    def test_busqueda_publica_por_nombre_modelo_categoria_y_precio(self):
        otro = Producto.objects.create(
            proveedor=self.proveedor, nombre='Bujía', categoria='mecanica_automotriz',
            precio=500, stock=1,
        )
        casos = [
            ({'q': ' premium '}, [self.producto]),
            ({'q': 'interno'}, [self.producto]),
            ({'categoria': 'mecanica_automotriz', 'orden': 'precio_asc'}, [otro, self.producto]),
            ({'orden': 'precio_desc'}, [self.producto, otro]),
        ]
        for filtros, esperados in casos:
            with self.subTest(filtros=filtros):
                response = self.client.get(reverse('buscar_repuestos'), filtros)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['productos'], esperados)

    def test_ocultos_y_proveedores_no_habilitados_no_aparecen(self):
        self.producto.disponible = False
        self.producto.save(update_fields=['disponible'])
        response = self.client.get(reverse('buscar_repuestos'))
        self.assertNotContains(response, self.producto.nombre)
        self.assertEqual(response.context['categorias'], [])
        self.producto.disponible = True
        self.producto.save(update_fields=['disponible'])
        for estado, aprobado, activo in [
            ('pendiente', True, True), ('rechazado', True, True),
            ('suspendido', True, True), ('aprobado', False, True),
            ('aprobado', True, False),
        ]:
            with self.subTest(estado=estado, aprobado=aprobado, activo=activo):
                Proveedor.objects.filter(pk=self.proveedor.pk).update(
                    estado=estado, is_approved=aprobado,
                )
                User.objects.filter(pk=self.proveedor.usuario_id).update(is_active=activo)
                response = self.client.get(reverse('buscar_repuestos'))
                self.assertNotContains(response, self.producto.nombre)
                self.assertEqual(response.context['categorias'], [])

    def test_interacciones_anonimas_redirigen_al_login(self):
        urls = [
            reverse('perfil_proveedor', args=[self.proveedor.pk]),
            reverse('crear_pedido', args=[self.producto.pk]),
            reverse('mis_creditos'),
        ]
        for url in urls:
            for metodo in (self.client.get, self.client.post):
                with self.subTest(url=url, metodo=metodo.__name__):
                    self.assertRedirects(metodo(url), f'{reverse("login")}?next={url}')

    def test_sin_coincidencias_muestra_mensaje(self):
        response = self.client.get(reverse('buscar_repuestos'), {'q': 'inexistente'})
        self.assertContains(response, 'No se encontraron repuestos para tu búsqueda.')
        self.assertNotContains(response, 'Ocurrió un error')

    def test_fallo_al_evaluar_productos_o_categorias_muestra_error_y_permite_reintentar(self):
        def consulta_fallida():
            raise OperationalError('Detalle interno de base de datos')
            yield  # Simula un QuerySet que falla recién al ser evaluado.

        class ConsultaFallida:
            def count(self):
                return 1

            def __getitem__(self, _slice):
                return consulta_fallida()

            def __iter__(self):
                return consulta_fallida()

        for selector in ('buscar_productos', 'categorias_publicadas'):
            with self.subTest(selector=selector):
                with patch(f'apps.catalogo.search.{selector}', return_value=ConsultaFallida()):
                    with self.assertLogs('apps.catalogo.search', level='ERROR'):
                        response = self.client.get(reverse('buscar_repuestos'), {
                            'q': 'Filtro', 'categoria': 'mecanica_automotriz', 'orden': 'precio_asc',
                        })
                self.assertContains(response, 'Ocurrió un error al realizar la búsqueda.', status_code=503)
                self.assertContains(response, 'Reintentar búsqueda', status_code=503)
                self.assertContains(response, 'value="Filtro"', status_code=503)
                self.assertContains(response, 'value="mecanica_automotriz" selected', status_code=503)
                self.assertNotContains(response, 'Detalle interno', status_code=503)
                self.assertNotContains(response, 'No se encontraron repuestos', status_code=503)

    def test_tecnico_habilitado_conserva_datos_y_acciones(self):
        self.client.force_login(self.tecnico.usuario)
        response = self.client.get(reverse('buscar_repuestos'))
        for texto in (self.proveedor.nombre_negocio, self.proveedor.direccion,
                      self.producto.modelo, 'Stock: 7', 'Solicitar'):
            self.assertContains(response, texto)

    def test_tecnico_suspendido_no_accede_a_funciones_privadas(self):
        self.tecnico.estado = 'suspendido'
        self.tecnico.save(update_fields=['estado'])
        self.client.force_login(self.tecnico.usuario)
        response = self.client.get(reverse('buscar_repuestos'))
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
