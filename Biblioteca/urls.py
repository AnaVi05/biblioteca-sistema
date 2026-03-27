from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from usuario import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('catalogo/', include('catalogo.urls')),
    path('', include('prestamo.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
