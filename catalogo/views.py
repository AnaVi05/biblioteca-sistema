from django.shortcuts import render
from .models import Libro, Categoria, Autor

def catalogo_lista(request):
    # Obtener todos los libros
    libros = Libro.objects.all().order_by('-id')  # Los más nuevos primero
    
    # Obtener categorías y autores para filtros
    categorias = Categoria.objects.all()
    autores = Autor.objects.all()
    
    # Filtros (si vienen por GET)
    categoria_id = request.GET.get('categoria')
    autor_id = request.GET.get('autor')
    busqueda = request.GET.get('q')
    
    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)
    
    if autor_id:
        libros = libros.filter(autores__id=autor_id)
    
    if busqueda:
        libros = libros.filter(titulo__icontains=busqueda) | \
                 libros.filter(autores__nombre__icontains=busqueda) | \
                 libros.filter(autores__apellido__icontains=busqueda)
    
    context = {
        'libros': libros,
        'categorias': categorias,
        'autores': autores,
    }
    return render(request, 'catalogo/lista.html', context)