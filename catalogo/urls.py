from django.urls import path
from . import views
from prestamo.admin import admin_site

urlpatterns = [
    # URLs públicas
    path('', views.catalogo_lista, name='catalogo_lista'),
    path('libro/<int:libro_id>/', views.catalogo_detalle, name='catalogo_detalle'),
    
    # Gestión de libros (bibliotecario)
    path('gestion/libros/', views.gestionar_libros, name='gestionar_libros'),
    path('gestion/libros/nuevo/', views.libro_crear, name='libro_crear'),
    path('gestion/libros/editar/<int:libro_id>/', views.libro_editar, name='libro_editar'),
    
    # Gestión de ejemplares (bibliotecario)
    path('gestion/ejemplares/', views.gestionar_ejemplares, name='gestionar_ejemplares'),
    path('gestion/ejemplares/libro/<int:libro_id>/', views.gestionar_ejemplares, name='gestionar_ejemplares_por_libro'),
    path('gestion/ejemplares/nuevo/<int:libro_id>/', views.ejemplar_crear, name='ejemplar_crear'),
    path('gestion/ejemplares/editar/<int:ejemplar_id>/', views.ejemplar_editar, name='ejemplar_editar'),
    path('admin/', admin_site.urls),

    path('gestion/libros/baja/<int:libro_id>/', views.libro_dar_baja, name='libro_dar_baja'),
    path('gestion/libros/alta/<int:libro_id>/', views.libro_dar_alta, name='libro_dar_alta'),
]