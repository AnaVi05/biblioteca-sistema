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
]