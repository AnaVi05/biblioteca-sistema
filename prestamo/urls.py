from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_prestamos, name='lista_prestamos'),
    path('nuevo/', views.crear_prestamo, name='crear_prestamo'),
    path('<int:pk>/', views.detalle_prestamo, name='detalle_prestamo'),
    path('<int:pk>/devolver/', views.devolver_prestamo, name='devolver_prestamo'),
    path('<int:pk>/extraviado/', views.marcar_extraviado, name='marcar_extraviado'),
    
    # URLs de Reservas
    path('reservar/<int:libro_id>/', views.reservar_libro, name='reservar_libro'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('cancelar-reserva/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    
    # URLs de Préstamos para usuarios
    path('registrar/<int:ejemplar_id>/', views.registrar_prestamo_usuario, name='registrar_prestamo_usuario'),
    path('mis-prestamos/', views.mis_prestamos, name='mis_prestamos'),
    path('mis-prestamos/devolver/<int:prestamo_id>/', views.devolver_prestamo_usuario, name='devolver_prestamo_usuario'),
    path('cancelar-solicitud/<int:prestamo_id>/', views.cancelar_solicitud, name='cancelar_solicitud'),
    
    # ========== PANEL BIBLIOTECARIO ==========
    path('bibliotecario/dashboard/', views.dashboard_bibliotecario, name='dashboard_bibliotecario'),
    path('bibliotecario/prestamos/nuevo/', views.prestamo_nuevo_bibliotecario, name='prestamo_nuevo_bibliotecario'),
    path('bibliotecario/devoluciones/', views.registrar_devolucion, name='registrar_devolucion'),
    path('bibliotecario/reservas/', views.gestionar_reservas, name='gestionar_reservas'),
    path('bibliotecario/multas/', views.gestionar_multas, name='gestionar_multas'),
    path('confirmar-prestamo/<int:prestamo_id>/', views.confirmar_prestamo, name='confirmar_prestamo'),
    path('bibliotecario/configuracion/', views.configuracion_panel, name='configuracion_panel'),
    path('bibliotecario/perfil/', views.mi_perfil, name='mi_perfil'),
    path('bibliotecario/buscar-usuario/', views.buscar_usuario, name='buscar_usuario'),


    # Reportes 
    path('reporte/prestamos-activos/', views.reporte_prestamos_activos, name='reporte_prestamos_activos'),
    path('reporte/devoluciones/', views.reporte_devoluciones, name='reporte_devoluciones'),
    path('reporte/reservas-expiradas/', views.reporte_reservas_expiradas, name='reporte_reservas_expiradas'),


    #Notificaciones 
    path('api/notificaciones/', views.api_notificaciones, name='api_notificaciones'),
]