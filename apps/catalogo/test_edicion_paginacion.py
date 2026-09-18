from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import OperationalError, close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.calificaciones.models import CalificacionProveedor
from apps.pedidos.services import aceptar_pedido
from apps.pedidos.test_integridad import DatosPedidoMixin
from apps.usuarios.models import Proveedor

from .forms import ProductoForm
from .models import Producto
from .paginacion import PRODUCTOS_POR_PAGINA
from .selectors import buscar_productos


def datos_edicion(form):
    return {nombre: valor for nombre, valor in form.initial.items() if nombre != 'imagen'}


class EdicionProductoTests(DatosPedidoMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.proveedor.usuario)
        self.url = reverse('editar_producto', args=[self.producto.pk])

    def test_formulario_antiguo_no_restaura_stock_ni_guarda_otros_campos(self):
        datos = datos_edicion(self.client.get(self.url).context['form'])
        pedido = self.comprar()
        aceptar_pedido(pedido=pedido)
        datos['nombre'] = 'Filtro editado'
        respuesta = self.client.post(self.url, datos)
        self.assertContains(respuesta, 'El producto cambió')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 9)
        self.assertEqual(self.producto.nombre, 'Filtro')
        # Una nueva lectura permite aplicar una corrección intencional de stock.
        datos = datos_edicion(self.client.get(self.url).context['form'])
        datos.update(nombre='Filtro editado', stock=8)
        self.assertRedirects(self.client.post(self.url, datos), reverse('catalogo_proveedor'))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(self.producto.nombre, 'Filtro editado')

    def test_dos_formularios_abiertos_no_pisan_ediciones(self):
        datos = datos_edicion(self.client.get(self.url).context['form'])
        self.client.post(self.url, {**datos, 'precio': '1200.00'})
        respuesta = self.client.post(self.url, {**datos, 'nombre': 'Nombre antiguo'})
        self.assertContains(respuesta, 'El producto cambió')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal('1200'))
        self.assertEqual(self.producto.nombre, 'Filtro')

    def test_version_ausente_alterada_o_de_otro_producto_no_guarda(self):
        datos = datos_edicion(self.client.get(self.url).context['form'])
        otro = Producto.objects.create(
            proveedor=self.proveedor, nombre='Otro', categoria='mecanica_automotriz',
            precio=1000, stock=10,
        )
        version_ajena = ProductoForm(instance=otro).initial['version_producto']
        for version in ('', 'alterada', version_ajena):
            with self.subTest(version=version):
                respuesta = self.client.post(self.url, {**datos, 'stock': 100, 'version_producto': version})
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context['form'].errors)
                self.producto.refresh_from_db()
                self.assertEqual(self.producto.stock, 10)

    def test_otro_proveedor_no_puede_editar(self):
        datos = datos_edicion(self.client.get(self.url).context['form'])
        otro = Proveedor.objects.create(
            usuario=User.objects.create_user(username='otro-editor'),
            nombre_negocio='Otro proveedor', direccion='CABA', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        self.client.force_login(otro.usuario)
        self.assertEqual(self.client.post(self.url, {**datos, 'stock': 100}).status_code, 404)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_creacion_no_requiere_version(self):
        respuesta = self.client.post(reverse('agregar_producto'), {
            'nombre': 'Nuevo', 'categoria': 'mecanica_automotriz',
            'precio': 1000, 'stock': 3, 'disponible': 'on',
        })
        self.assertRedirects(respuesta, reverse('catalogo_proveedor'))
        self.assertTrue(Producto.objects.filter(nombre='Nuevo', stock=3).exists())

    def test_admin_rechaza_stock_antiguo_y_permite_edicion_actual(self):
        admin = User.objects.create_superuser(username='admin-edicion')
        self.client.force_login(admin)
        url = reverse('admin:catalogo_producto_change', args=[self.producto.pk])
        datos = datos_edicion(self.client.get(url).context['adminform'].form)
        aceptar_pedido(pedido=self.comprar())
        respuesta = self.client.post(url, {**datos, '_save': 'Guardar'})
        self.assertContains(respuesta, 'El producto cambió')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 9)
        datos = datos_edicion(self.client.get(url).context['adminform'].form)
        respuesta = self.client.post(url, {**datos, 'nombre': 'Desde admin', '_save': 'Guardar'})
        self.assertEqual(respuesta.status_code, 302)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Desde admin')
        self.assertEqual(self.producto.stock, 9)


class PaginacionCatalogoTests(DatosPedidoMixin, TestCase):
    def agregar_productos(self, cantidad):
        return Producto.objects.bulk_create([
            Producto(
                proveedor=self.proveedor, nombre='Filtro', categoria='mecanica_automotriz',
                precio=1000, stock=2,
            ) for _ in range(cantidad)
        ])

    def test_busqueda_paginada_conserva_filtros_y_no_duplica_empates(self):
        self.agregar_productos(PRODUCTOS_POR_PAGINA)
        filtros = {'q': 'Filtro', 'categoria': 'mecanica_automotriz', 'orden': 'precio_asc'}
        primera = self.client.get(reverse('buscar_repuestos'), filtros)
        segunda = self.client.get(reverse('buscar_repuestos'), {**filtros, 'page': 2})
        ids_primera = [p.pk for p in primera.context['productos']]
        ids_segunda = [p.pk for p in segunda.context['productos']]
        self.assertEqual(len(ids_primera), PRODUCTOS_POR_PAGINA)
        self.assertEqual(len(ids_segunda), 1)
        self.assertEqual(set(ids_primera) & set(ids_segunda), set())
        self.assertEqual(ids_primera + ids_segunda, list(Producto.objects.order_by('pk').values_list('pk', flat=True)))
        self.assertContains(primera, 'q=Filtro&amp;categoria=mecanica_automotriz&amp;orden=precio_asc&amp;page=2')
        self.assertContains(segunda, 'Página 2 de 2')
        self.assertEqual(primera.context['pagina'].paginator.count, PRODUCTOS_POR_PAGINA + 1)

    def test_paginas_invalidas_no_generan_error_y_catalogo_vacio_funciona(self):
        self.agregar_productos(PRODUCTOS_POR_PAGINA)
        for valor, numero in [('abc', 1), ('999', 2), ('-1', 2)]:
            with self.subTest(valor=valor):
                respuesta = self.client.get(reverse('buscar_repuestos'), {'page': valor})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['pagina'].number, numero)
        respuesta = self.client.get(reverse('buscar_repuestos'), {'q': 'sin coincidencias'})
        self.assertEqual(respuesta.context['productos'], [])
        self.assertEqual(respuesta.context['pagina'].paginator.count, 0)

    def test_catalogo_propio_paginado_no_incluye_productos_ajenos(self):
        self.agregar_productos(PRODUCTOS_POR_PAGINA)
        otro = Proveedor.objects.create(
            usuario=User.objects.create_user(username='catalogo-ajeno'),
            nombre_negocio='Otro proveedor', direccion='CABA', rubro='mecanica_automotriz',
            estado='aprobado', is_approved=True,
        )
        Producto.objects.create(
            proveedor=otro, nombre='Ajeno', categoria='mecanica_automotriz', precio=1000, stock=1,
        )
        self.client.force_login(self.proveedor.usuario)
        url = reverse('catalogo_proveedor')
        primera = self.client.get(url)
        segunda = self.client.get(url, {'page': 2})
        self.assertEqual(len(primera.context['productos']), PRODUCTOS_POR_PAGINA)
        self.assertEqual(len(segunda.context['productos']), 1)
        self.assertEqual(primera.context['pagina'].paginator.count, PRODUCTOS_POR_PAGINA + 1)
        self.assertTrue(all(p.proveedor_id == self.proveedor.pk for p in primera.context['productos']))
        self.assertContains(primera, 'page=2')

    def test_consultas_publicas_acotadas_y_resultados_limitados_en_sql(self):
        self.agregar_productos(PRODUCTOS_POR_PAGINA + 5)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(reverse('buscar_repuestos'))
        self.assertEqual(len(consultas), 3)
        self.assertEqual(len(respuesta.context['productos']), PRODUCTOS_POR_PAGINA)
        consulta_productos = next(q['sql'] for q in consultas if 'LIMIT 24' in q['sql'])
        self.assertNotIn('pedidos_pedido', consulta_productos)

    def test_calificaciones_y_ventas_correctas_sin_consultas_por_tarjeta(self):
        pedido = self.comprar()
        pedido.estado = 'completado'
        pedido.save(update_fields=['estado'])
        CalificacionProveedor.objects.create(
            pedido=pedido, tecnico=self.tecnico, proveedor=self.proveedor, estrellas=4,
        )
        otro = self.comprar()
        otro.estado = 'completado'
        otro.save(update_fields=['estado'])
        CalificacionProveedor.objects.create(
            pedido=otro, tecnico=self.tecnico, proveedor=self.proveedor, estrellas=5,
        )
        with self.assertNumQueries(1):
            resultados = list(buscar_productos(orden='mas_vendidos').con_calificacion_proveedor())
        self.assertEqual(resultados[0].unidades_vendidas, 2)
        self.assertEqual(resultados[0].calificacion_proveedor, 4.5)
        self.client.force_login(self.tecnico.usuario)
        with CaptureQueriesContext(connection) as consultas_una:
            una = self.client.get(reverse('buscar_repuestos'))
        self.assertContains(una, '4,5')
        self.agregar_productos(PRODUCTOS_POR_PAGINA - 1)
        with CaptureQueriesContext(connection) as consultas_varias:
            varias = self.client.get(reverse('buscar_repuestos'))
        self.assertEqual(len(consultas_una), len(consultas_varias))
        self.assertLessEqual(len(consultas_varias), 7)
        self.assertEqual(len(varias.context['productos']), PRODUCTOS_POR_PAGINA)

    def test_sin_calificaciones_no_muestra_estrellas(self):
        self.client.force_login(self.tecnico.usuario)
        respuesta = self.client.get(reverse('buscar_repuestos'))
        self.assertIsNone(respuesta.context['productos'][0].calificacion_proveedor)
        self.assertNotContains(respuesta, '★')


@skipUnlessDBFeature('has_select_for_update')
class BloqueoEdicionProductoTests(DatosPedidoMixin, TransactionTestCase):
    def test_aceptacion_espera_validacion_y_guardado_de_la_edicion(self):
        pedido = self.comprar()
        self.client.force_login(self.proveedor.usuario)
        url = reverse('editar_producto', args=[self.producto.pk])
        datos = datos_edicion(self.client.get(url).context['form'])
        datos['nombre'] = 'Editado simultáneamente'
        validando = Event()
        continuar = Event()
        clean_original = ProductoForm.clean

        def clean_pausado(form):
            resultado = clean_original(form)
            validando.set()
            if not continuar.wait(timeout=10):
                raise RuntimeError('No se liberó la edición de prueba.')
            return resultado

        def editar():
            close_old_connections()
            try:
                return self.client.post(url, datos).status_code
            finally:
                connections['default'].close()

        def aceptar_con_timeout():
            close_old_connections()
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '500ms'")
                aceptar_pedido(pedido=pedido)
            finally:
                connections['default'].close()

        with patch.object(ProductoForm, 'clean', clean_pausado):
            with ThreadPoolExecutor(max_workers=2) as executor:
                edicion = executor.submit(editar)
                try:
                    self.assertTrue(validando.wait(timeout=5))
                    aceptacion = executor.submit(aceptar_con_timeout)
                    with self.assertRaises(OperationalError) as error:
                        aceptacion.result(timeout=5)
                    self.assertEqual(error.exception.__cause__.pgcode, '55P03')
                finally:
                    continuar.set()
                self.assertEqual(edicion.result(timeout=5), 302)
        aceptar_pedido(pedido=pedido)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Editado simultáneamente')
        self.assertEqual(self.producto.stock, 9)
