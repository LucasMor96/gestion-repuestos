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

    # Pedidos de repuestos – US-07 / US-08
    path('pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/crear/<int:producto_pk>/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/cancelar/<int:pk>/', views.cancelar_pedido, name='cancelar_pedido'),
    path('pedidos/recibidos/', views.pedidos_recibidos, name='pedidos_recibidos'),
    path('pedidos/detalle/<int:pk>/', views.detalle_pedido_proveedor, name='detalle_pedido_proveedor'),
    path('pedidos/gestionar/<int:pk>/', views.gestionar_pedido, name='gestionar_pedido'),

    # Moderación (solo staff)
    path('moderacion/', views.panel_moderacion, name='panel_moderacion'),
    path('moderacion/aprobar/<str:tipo>/<int:pk>/', views.aprobar_usuario, name='aprobar_usuario'),
    path('moderacion/rechazar/<str:tipo>/<int:pk>/', views.rechazar_usuario, name='rechazar_usuario'),
    path('moderacion/suspender/<str:tipo>/<int:pk>/', views.suspender_usuario, name='suspender_usuario'),
    path('moderacion/solicitar-info/<str:tipo>/<int:pk>/', views.solicitar_info, name='solicitar_info'),
]
