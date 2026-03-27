from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from usuario import views
from django.conf import settings
from django.conf.urls.static import static
from prestamo.views import mi_perfil, configuracion_panel

# Vista de redirección según rol
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
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', cerrar_sesion, name='logout'),
    path('', redirigir_inicio, name='home'),
    path('registro/', views.registrar_usuario, name='registro'),
    
    # Cambio de contraseña
    path('cambiar-contrasena/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url='/cambiar-contrasena/hecho/'
    ), name='password_change'),
    path('cambiar-contrasena/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    
    # Perfil y configuración
    path('perfil/', mi_perfil, name='mi_perfil'),
    path('configuracion/', configuracion_panel, name='configuracion_panel'),
    
    path('catalogo/', include('catalogo.urls')),
    path('', include('prestamo.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)