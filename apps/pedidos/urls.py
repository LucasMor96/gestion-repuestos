from django.urls import path

from . import views


urlpatterns = [
    path('pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedidos/exportar/', views.exportar_historial, name='exportar_historial'),
    path('pedidos/crear/<int:producto_pk>/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/cancelar/<int:pk>/', views.cancelar_pedido, name='cancelar_pedido'),
    path('pedidos/recibidos/', views.pedidos_recibidos, name='pedidos_recibidos'),
    path('pedidos/detalle/<int:pk>/', views.detalle_pedido_proveedor, name='detalle_pedido_proveedor'),
    path('pedidos/gestionar/<int:pk>/', views.gestionar_pedido, name='gestionar_pedido'),
    path('pedidos/completar/<int:pk>/', views.completar_pedido, name='completar_pedido'),
]
