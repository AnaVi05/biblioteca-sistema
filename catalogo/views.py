from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Libro, Categoria, Autor, Editorial, Ejemplar


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


def catalogo_detalle(request, libro_id):
    """Vista detalle de un libro para usuarios"""
    libro = get_object_or_404(Libro, id=libro_id)
    ejemplares_disponibles = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
    
    context = {
        'libro': libro,
        'ejemplares_disponibles': ejemplares_disponibles,
    }
    return render(request, 'catalogo/detalle.html', context)


# ========== VISTAS PARA GESTIÓN DE LIBROS (BIBLIOTECARIO) ==========

@staff_member_required
def gestionar_libros(request):
    """Lista de libros para administrar"""
    libros = Libro.objects.all().select_related('editorial', 'categoria').order_by('titulo')
    
    # Búsqueda
    search = request.GET.get('search', '')
    if search:
        libros = libros.filter(titulo__icontains=search)
    
    context = {
        'libros': libros,
        'search': search,
    }
    return render(request, 'bibliotecario/libros_lista.html', context)


@staff_member_required
def libro_crear(request):
    """Crear nuevo libro"""
    if request.method == 'POST':
        try:
            libro = Libro.objects.create(
                isbn=request.POST.get('isbn'),
                titulo=request.POST.get('titulo'),
                anio_publicacion=request.POST.get('anio_publicacion') or None,
                descripcion=request.POST.get('descripcion'),
                editorial_id=request.POST.get('editorial'),
                categoria_id=request.POST.get('categoria'),
                cantidad_total=int(request.POST.get('cantidad_total', 0)),
                inventario_disponible=int(request.POST.get('inventario_disponible', 0))
            )
            
            # Agregar autores
            autores_ids = request.POST.getlist('autores')
            if autores_ids:
                libro.autores.set(autores_ids)
            
            messages.success(request, f'Libro "{libro.titulo}" creado exitosamente')
            return redirect('gestionar_libros')
            
        except Exception as e:
            messages.error(request, f'Error al crear libro: {str(e)}')
    
    editoriales = Editorial.objects.all()
    categorias = Categoria.objects.all()
    autores = Autor.objects.all()
    
    context = {
        'editoriales': editoriales,
        'categorias': categorias,
        'autores': autores,
    }
    return render(request, 'bibliotecario/libro_form.html', context)


@staff_member_required
def libro_editar(request, libro_id):
    """Editar libro existente"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    if request.method == 'POST':
        try:
            libro.isbn = request.POST.get('isbn')
            libro.titulo = request.POST.get('titulo')
            libro.anio_publicacion = request.POST.get('anio_publicacion') or None
            libro.descripcion = request.POST.get('descripcion')
            libro.editorial_id = request.POST.get('editorial')
            libro.categoria_id = request.POST.get('categoria')
            libro.cantidad_total = int(request.POST.get('cantidad_total', 0))
            libro.inventario_disponible = int(request.POST.get('inventario_disponible', 0))
            libro.save()
            
            # Actualizar autores
            autores_ids = request.POST.getlist('autores')
            libro.autores.set(autores_ids)
            
            messages.success(request, f'Libro "{libro.titulo}" actualizado exitosamente')
            return redirect('gestionar_libros')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar libro: {str(e)}')
    
    editoriales = Editorial.objects.all()
    categorias = Categoria.objects.all()
    autores = Autor.objects.all()
    autores_seleccionados = libro.autores.values_list('id', flat=True)
    
    context = {
        'libro': libro,
        'editoriales': editoriales,
        'categorias': categorias,
        'autores': autores,
        'autores_seleccionados': list(autores_seleccionados),
    }
    return render(request, 'bibliotecario/libro_form.html', context)


@staff_member_required
def gestionar_ejemplares(request, libro_id=None):
    """Gestionar ejemplares por libro"""
    if libro_id:
        libro = get_object_or_404(Libro, id=libro_id)
        ejemplares = Ejemplar.objects.filter(libro=libro).order_by('codigo_inventario')
    else:
        libro = None
        ejemplares = Ejemplar.objects.all().select_related('libro').order_by('libro__titulo', 'codigo_inventario')
    
    # Búsqueda
    search = request.GET.get('search', '')
    if search:
        ejemplares = ejemplares.filter(codigo_inventario__icontains=search) | ejemplares.filter(libro__titulo__icontains=search)
    
    context = {
        'libro': libro,
        'ejemplares': ejemplares,
        'search': search,
    }
    return render(request, 'bibliotecario/ejemplares_lista.html', context)


@staff_member_required
def ejemplar_crear(request, libro_id):
    """Agregar nuevo ejemplar a un libro"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    if request.method == 'POST':
        try:
            ejemplar = Ejemplar.objects.create(
                libro=libro,
                codigo_inventario=request.POST.get('codigo_inventario'),
                estado_fisico=request.POST.get('estado_fisico'),
                disponibilidad=request.POST.get('disponibilidad'),
                ubicacion=request.POST.get('ubicacion')
            )
            
            # Actualizar cantidad total del libro
            libro.cantidad_total = Ejemplar.objects.filter(libro=libro).count()
            libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
            libro.save()
            
            messages.success(request, f'Ejemplar "{ejemplar.codigo_inventario}" agregado exitosamente')
            return redirect('gestionar_ejemplares_por_libro', libro_id=libro.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear ejemplar: {str(e)}')
    
    context = {
        'libro': libro,
        'estado_fisico_choices': Ejemplar.ESTADO_FISICO_CHOICES,
        'disponibilidad_choices': Ejemplar.DISPONIBILIDAD_CHOICES,
    }
    return render(request, 'bibliotecario/ejemplar_form.html', context)


@staff_member_required
def ejemplar_editar(request, ejemplar_id):
    """Editar ejemplar existente"""
    ejemplar = get_object_or_404(Ejemplar, id=ejemplar_id)
    
    if request.method == 'POST':
        try:
            ejemplar.estado_fisico = request.POST.get('estado_fisico')
            ejemplar.disponibilidad = request.POST.get('disponibilidad')
            ejemplar.ubicacion = request.POST.get('ubicacion')
            ejemplar.save()
            
            # Actualizar inventario del libro
            libro = ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
            libro.save()
            
            messages.success(request, f'Ejemplar "{ejemplar.codigo_inventario}" actualizado exitosamente')
            return redirect('gestionar_ejemplares_por_libro', libro_id=ejemplar.libro.id)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar ejemplar: {str(e)}')
    
    context = {
        'ejemplar': ejemplar,
        'estado_fisico_choices': Ejemplar.ESTADO_FISICO_CHOICES,
        'disponibilidad_choices': Ejemplar.DISPONIBILIDAD_CHOICES,
    }
    return render(request, 'bibliotecario/ejemplar_form.html', context)