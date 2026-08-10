from django.urls import path

from . import search, views


urlpatterns = [
    path('buscar/', search.buscar_repuestos, name='buscar_repuestos'),
    path('catalogo/', views.catalogo_proveedor, name='catalogo_proveedor'),
    path('catalogo/agregar/', views.agregar_producto, name='agregar_producto'),
    path('catalogo/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('catalogo/eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('catalogo/toggle/<int:pk>/', views.toggle_disponibilidad, name='toggle_disponibilidad'),
]
