"""
URL configuration for Biblioteca project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from usuario import views
from django.conf import settings
from django.conf.urls.static import static
from datetime import date
from prestamo.models import Prestamo, Reserva, Multa


# ========== VISTA PRINCIPAL ==========
def redirigir_inicio(request):
    """Redirige según el rol del usuario"""
    if request.user.is_staff:
        # Bibliotecario: va al dashboard
        return redirect('dashboard_bibliotecario')
    else:
        # Usuario normal: dashboard con datos reales
        socio = request.user.socio
    
    # Préstamos activos (libros que el usuario ya tiene)
    prestamos_activos = Prestamo.objects.filter(
        socio=socio,
        estado='ACTIVO'
    )
    
    # Reservas activas (pendientes)
    reservas_activas = Reserva.objects.filter(
        socio=socio,
        estado='PENDIENTE'
    )
    
    # Multas pendientes
    multas_pendientes = Multa.objects.filter(
        prestamo__socio=socio,
        estado='PENDIENTE'
    )
    
    # Calcular total de multas
    total_multas = sum(multa.monto_total for multa in multas_pendientes) if multas_pendientes else 0
    
    # Próxima devolución (el préstamo activo que vence antes)
    proxima_devolucion = prestamos_activos.order_by('fecha_vencimiento').first()
    proxima_devolucion_dias = None
    if proxima_devolucion:
        dias = (proxima_devolucion.fecha_vencimiento - date.today()).days
        proxima_devolucion_dias = dias if dias > 0 else 0
    
    # Actividad reciente (últimos 3 préstamos)
    actividad_reciente = Prestamo.objects.filter(
        socio=socio
    ).order_by('-fecha_prestamo')[:3]
    
    context = {
        'prestamos_activos': prestamos_activos,
        'reservas_activas': reservas_activas,
        'multas_pendientes': multas_pendientes,
        'total_multas': total_multas,
        'proxima_devolucion': proxima_devolucion,
        'proxima_devolucion_dias': proxima_devolucion_dias,
        'actividad_reciente': actividad_reciente,
        'hoy': date.today(),
    }
    
    if request.user.is_staff:
        return render(request, 'base/menu_bibliotecario.html', context)
    else:
        return render(request, 'base/menu_usuario.html', context)


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
    path('perfil/', views.mi_perfil, name='mi_perfil'),
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
