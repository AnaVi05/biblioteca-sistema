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
from datetime import date, timedelta
from prestamo.models import Prestamo, Reserva, Multa
from django.contrib.auth.views import LogoutView
from prestamo.admin import admin_site  # Importa el admin personalizado


# ========== VISTA PRINCIPAL ==========
def redirigir_inicio(request):
    """Redirige según el rol del usuario y pasa datos reales al dashboard"""
    if request.user.is_staff:
        return redirect('dashboard_bibliotecario')
    else:
        # ========== DATOS REALES PARA EL DASHBOARD ==========
        from datetime import date, timedelta
        from prestamo.models import Prestamo, Reserva, Multa
        
        try:
            socio = request.user.socio
        except:
            # Si el usuario no tiene perfil de socio, mostrar dashboard vacío
            context = {
                'prestamos_activos': [],
                'reservas_activas': [],
                'multas_pendientes': [],
                'total_multas': 0,
                'proxima_devolucion': None,
                'proxima_devolucion_dias': None,
                'actividad_reciente': [],
                'prestamos_proximos_vencer': [],
                'hoy': date.today(),
            }
            return render(request, 'base/menu_usuario.html', context)
        
        # Préstamos activos
        prestamos_activos = Prestamo.objects.filter(socio=socio, estado='ACTIVO')
        
        # Reservas activas
        reservas_activas = Reserva.objects.filter(socio=socio, estado='PENDIENTE')
        
        # Multas pendientes
        multas_pendientes = Multa.objects.filter(prestamo__socio=socio, estado='PENDIENTE')
        total_multas = sum(m.monto_total for m in multas_pendientes)
        
        # Próxima devolución
        proxima_devolucion = prestamos_activos.order_by('fecha_vencimiento').first()
        proxima_devolucion_dias = None
        if proxima_devolucion:
            dias = (proxima_devolucion.fecha_vencimiento - date.today()).days
            proxima_devolucion_dias = dias if dias > 0 else 0
        
        # 🆕 Préstamos próximos a vencer (próximos 3 días)
        prestamos_proximos_vencer = Prestamo.objects.filter(
            socio=socio,
            estado='ACTIVO',
            fecha_vencimiento__gte=date.today(),
            fecha_vencimiento__lte=date.today() + timedelta(days=3)
        )
        
        # Actividad reciente
        actividad_reciente = Prestamo.objects.filter(socio=socio).order_by('-fecha_prestamo')[:3]
        
        context = {
            'prestamos_activos': prestamos_activos,
            'reservas_activas': reservas_activas,
            'multas_pendientes': multas_pendientes,
            'total_multas': total_multas,
            'proxima_devolucion': proxima_devolucion,
            'proxima_devolucion_dias': proxima_devolucion_dias,
            'prestamos_proximos_vencer': prestamos_proximos_vencer,  # 🆕 Agregado
            'actividad_reciente': actividad_reciente,
            'hoy': date.today(),
        }
        
        return render(request, 'base/menu_usuario.html', context)


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