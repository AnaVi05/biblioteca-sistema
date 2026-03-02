from django.urls import path
from . import views

urlpatterns = [
    # Lista de socios
    path('', views.lista_socios, name='lista_socios'),
    
    # Detalle de socio
    path('<int:pk>/', views.detalle_socio, name='detalle_socio'),
    
    # Crear nuevo socio
    path('nuevo/', views.crear_socio, name='crear_socio'),
    
    # Editar socio
    path('<int:pk>/editar/', views.editar_socio, name='editar_socio'),
    
    # Eliminar socio
    path('<int:pk>/eliminar/', views.eliminar_socio, name='eliminar_socio'),
    
    # Buscar socios
    path('buscar/', views.buscar_socios, name='buscar_socios'),
]