from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro_tipo, name='registro_tipo'),
    path('registro/tecnico/', views.registro_tecnico, name='registro_tecnico'),
    path('registro/proveedor/', views.registro_proveedor, name='registro_proveedor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('espera-aprobacion/', views.espera_aprobacion, name='espera_aprobacion'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Perfil
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/tecnico/<int:pk>/', views.perfil_tecnico, name='perfil_tecnico'),
    path('perfil/proveedor/<int:pk>/', views.perfil_proveedor, name='perfil_proveedor'),

    # Búsqueda
    path('buscar/', views.buscar_repuestos, name='buscar_repuestos'),

    # Catálogo del proveedor (US-06)
    path('catalogo/', views.catalogo_proveedor, name='catalogo_proveedor'),
    path('catalogo/agregar/', views.agregar_producto, name='agregar_producto'),
    path('catalogo/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('catalogo/eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('catalogo/toggle/<int:pk>/', views.toggle_disponibilidad, name='toggle_disponibilidad'),

    # Pedidos de repuestos – US-07 / US-08 / US-09
    path('pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/exportar/', views.exportar_historial, name='exportar_historial'),
    path('pedidos/crear/<int:producto_pk>/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/cancelar/<int:pk>/', views.cancelar_pedido, name='cancelar_pedido'),
    path('pedidos/recibidos/', views.pedidos_recibidos, name='pedidos_recibidos'),
    path('pedidos/detalle/<int:pk>/', views.detalle_pedido_proveedor, name='detalle_pedido_proveedor'),
    path('pedidos/gestionar/<int:pk>/', views.gestionar_pedido, name='gestionar_pedido'),

    # Completar pedido + Calificaciones – US-13 / US-14
    path('pedidos/completar/<int:pk>/', views.completar_pedido, name='completar_pedido'),
    path('calificaciones/proveedor/<int:pedido_pk>/', views.calificar_proveedor, name='calificar_proveedor'),
    path('calificaciones/tecnico/<int:pedido_pk>/', views.calificar_tecnico, name='calificar_tecnico'),

    # Crédito comercial – US-10 / US-11 / US-12
    path('credito/', views.mis_creditos, name='mis_creditos'),
    path('credito/gestionar/', views.gestionar_creditos_proveedor, name='gestionar_creditos_proveedor'),
    path('credito/asignar/', views.asignar_credito, name='asignar_credito'),
    path('credito/revocar/<int:pk>/', views.revocar_credito, name='revocar_credito'),
    path('credito/deudas/', views.deudas_tecnicos, name='deudas_tecnicos'),
    path('credito/deudas/<int:pk>/', views.detalle_deuda_tecnico, name='detalle_deuda_tecnico'),
    path('credito/saldar/<int:pk>/', views.marcar_deuda_saldada, name='marcar_deuda_saldada'),

    # Moderación (solo staff)
    path('moderacion/', views.panel_moderacion, name='panel_moderacion'),
    path('moderacion/aprobar/<str:tipo>/<int:pk>/', views.aprobar_usuario, name='aprobar_usuario'),
    path('moderacion/rechazar/<str:tipo>/<int:pk>/', views.rechazar_usuario, name='rechazar_usuario'),
    path('moderacion/suspender/<str:tipo>/<int:pk>/', views.suspender_usuario, name='suspender_usuario'),
    path('moderacion/solicitar-info/<str:tipo>/<int:pk>/', views.solicitar_info, name='solicitar_info'),
]
