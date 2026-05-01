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
    path('reporte/reservas-expiradas/', views.reporte_reservas_expiradas, name='reporte_reservas_expiradas'),
    path('reporte/usuarios-activos/', views.reporte_usuarios_activos, name='reporte_usuarios_activos'),
    path('reporte/usuarios-morosos/', views.reporte_usuarios_morosos, name='reporte_usuarios_morosos'),
    path('reporte/usuarios-inhabilitados/', views.reporte_usuarios_inhabilitados, name='reporte_usuarios_inhabilitados'),
    path('reporte/prestamos-vencidos/', views.reporte_prestamos_vencidos, name='reporte_prestamos_vencidos'),
    path('reporte/libros-demanda/', views.reporte_libros_demanda, name='reporte_libros_demanda'),


    #Notificaciones 
    path('api/notificaciones/', views.api_notificaciones, name='api_notificaciones'),
    path('subir-comprobante/<int:multa_id>/', views.subir_comprobante, name='subir_comprobante'),
 ]
