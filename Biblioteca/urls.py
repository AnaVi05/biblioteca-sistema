"""
URL configuration for Biblioteca project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from usuario import views
from django.conf import settings
from django.conf.urls.static import static
from datetime import date
from prestamo.models import Prestamo, Reserva, Multa
from django.contrib.auth.views import LogoutView
from prestamo.admin import admin_site  # Importa el admin personalizado


# ========== VISTA PRINCIPAL ==========
def redirigir_inicio(request):
    """Redirige según el rol del usuario"""
    if request.user.is_staff:
        return redirect('dashboard_bibliotecario')
    else:
        return render(request, 'base/menu_usuario.html')


def cerrar_sesion(request):
    logout(request)
    return redirect('login')


urlpatterns = [
    # Admin personalizado
    path('admin/', admin_site.urls),
    
    # Logout del admin
    path('admin/logout/', LogoutView.as_view(next_page='/admin/login/'), name='admin_logout'),
    
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', cerrar_sesion, name='logout'),
    
    # Redirección principal
    path('', redirigir_inicio, name='home'),
    
    # Apps
    path('registro/', views.registrar_usuario, name='registro'),
    path('catalogo/', include('catalogo.urls')),
    path('', include('prestamo.urls')),
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    
    # Cambio de contraseña para usuarios normales
    path('cambiar-contrasena/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url='/cambiar-contrasena/hecho/'
    ), name='password_change'),
    path('cambiar-contrasena/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('configuracion/', views.configuracion, name='configuracion'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
