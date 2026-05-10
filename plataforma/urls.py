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

    # Moderación (solo staff)
    path('moderacion/', views.panel_moderacion, name='panel_moderacion'),
    path('moderacion/aprobar/<str:tipo>/<int:pk>/', views.aprobar_usuario, name='aprobar_usuario'),
    path('moderacion/rechazar/<str:tipo>/<int:pk>/', views.rechazar_usuario, name='rechazar_usuario'),
    path('moderacion/suspender/<str:tipo>/<int:pk>/', views.suspender_usuario, name='suspender_usuario'),
    path('moderacion/solicitar-info/<str:tipo>/<int:pk>/', views.solicitar_info, name='solicitar_info'),
]
