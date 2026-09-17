from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import moderacion, views


urlpatterns = [
    path('registro/', views.registro_tipo, name='registro_tipo'),
    path('registro/tecnico/', views.registro_tecnico, name='registro_tecnico'),
    path('registro/proveedor/', views.registro_proveedor, name='registro_proveedor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path(
        'password-reset/',
        views.password_recovery,
        name='password_reset',
    ),
    path(
        'password-cambiar/',
        auth_views.PasswordChangeView.as_view(
            template_name='usuarios/password_change_form.html',
            success_url=reverse_lazy('password_change_done'),
        ),
        name='password_change',
    ),
    path(
        'password-cambiar/completo/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='usuarios/password_change_done.html',
        ),
        name='password_change_done',
    ),
    path('espera-aprobacion/', views.espera_aprobacion, name='espera_aprobacion'),
    path('moderacion/imagenes/<int:pk>/', views.imagen_moderacion, name='imagen_moderacion'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/tecnico/<int:pk>/', views.perfil_tecnico, name='perfil_tecnico'),
    path('perfil/proveedor/<int:pk>/', views.perfil_proveedor, name='perfil_proveedor'),
    path('moderacion/', moderacion.panel_moderacion, name='panel_moderacion'),
    path('moderacion/aprobar/<str:tipo>/<int:pk>/', moderacion.aprobar_usuario, name='aprobar_usuario'),
    path('moderacion/rechazar/<str:tipo>/<int:pk>/', moderacion.rechazar_usuario, name='rechazar_usuario'),
    path('moderacion/suspender/<str:tipo>/<int:pk>/', moderacion.suspender_usuario, name='suspender_usuario'),
    path('moderacion/solicitar-info/<str:tipo>/<int:pk>/', moderacion.solicitar_info, name='solicitar_info'),
]
