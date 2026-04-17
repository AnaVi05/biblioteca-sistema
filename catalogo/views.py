from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Libro, Categoria, Autor, Editorial, Ejemplar


def catalogo_lista(request):
    # Solo libros activos (para usuarios)
    libros = Libro.objects.filter(activo=True).order_by('-id')
    
    categorias = Categoria.objects.all()
    autores = Autor.objects.all()
    
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
    libro = get_object_or_404(Libro, id=libro_id, activo=True)
    ejemplares_disponibles = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
    
    context = {
        'libro': libro,
        'ejemplares_disponibles': ejemplares_disponibles,
    }
    return render(request, 'catalogo/detalle.html', context)


# ========== VISTAS PARA GESTIÓN DE LIBROS (BIBLIOTECARIO) ==========

@staff_member_required
def gestionar_libros(request):
    """Lista de libros para administrar (bibliotecario ve todos)"""
    libros = Libro.objects.all().select_related('editorial', 'categoria').order_by('-activo', 'titulo')
    
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
    """Crear nuevo libro con ejemplar automático"""
    if request.method == 'POST':
        try:
            # Crear el libro (con cantidades iniciales en 1)
            libro = Libro.objects.create(
                isbn=request.POST.get('isbn'),
                titulo=request.POST.get('titulo'),
                anio_publicacion=request.POST.get('anio_publicacion') or None,
                descripcion=request.POST.get('descripcion'),
                editorial_id=request.POST.get('editorial'),
                categoria_id=request.POST.get('categoria'),
                cantidad_total=1,
                inventario_disponible=1,
                activo=True
            )
            
            autores_ids = request.POST.getlist('autores')
            if autores_ids:
                libro.autores.set(autores_ids)
            
            # Crear ejemplar con los datos del formulario
            codigo_inventario = request.POST.get('codigo_inventario')
            if not codigo_inventario:
                codigo_inventario = f"AUTO-{libro.id:04d}"
            
            estado_fisico = request.POST.get('estado_fisico', 'BUENO')
            disponibilidad = request.POST.get('disponibilidad', 'DISPONIBLE')
            ubicacion = request.POST.get('ubicacion', '')
            
            Ejemplar.objects.create(
                libro=libro,
                codigo_inventario=codigo_inventario,
                estado_fisico=estado_fisico,
                disponibilidad=disponibilidad,
                ubicacion=ubicacion
            )
            
            # Actualizar cantidades reales
            libro.cantidad_total = Ejemplar.objects.filter(libro=libro).count()
            libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
            libro.save()
            
            messages.success(request, f'✅ Libro "{libro.titulo}" creado exitosamente con un ejemplar')
            return redirect('gestionar_libros')
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear libro: {str(e)}')
    
    editoriales = Editorial.objects.all()
    categorias = Categoria.objects.all()
    autores = Autor.objects.all()
    
    context = {
        'editoriales': editoriales,
        'categorias': categorias,
        'autores': autores,
        'estado_fisico_choices': Ejemplar.ESTADO_FISICO_CHOICES,
        'disponibilidad_choices': Ejemplar.DISPONIBILIDAD_CHOICES,
    }
    return render(request, 'bibliotecario/libro_form.html', context)


@staff_member_required
def libro_editar(request, libro_id):
    """Editar libro existente"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    if request.method == 'POST':
        try:
            cantidad_total = int(request.POST.get('cantidad_total', 0))
            inventario_disponible = int(request.POST.get('inventario_disponible', 0))
            
            # Validaciones
            if cantidad_total < 0:
                messages.error(request, '❌ La cantidad total no puede ser negativa')
                return redirect('libro_editar', libro_id=libro.id)
            
            if inventario_disponible < 0:
                messages.error(request, '❌ Los ejemplares disponibles no pueden ser negativos')
                return redirect('libro_editar', libro_id=libro.id)
            
            if inventario_disponible > cantidad_total:
                messages.error(request, '❌ Los ejemplares disponibles no pueden ser mayores al total')
                return redirect('libro_editar', libro_id=libro.id)
            
            # Si hay ejemplares, no permitir cantidad_total = 0
            tiene_ejemplares = Ejemplar.objects.filter(libro=libro).exists()
            if tiene_ejemplares and cantidad_total == 0:
                messages.error(request, '❌ No puedes establecer cantidad total 0 porque el libro tiene ejemplares')
                return redirect('libro_editar', libro_id=libro.id)
            
            libro.isbn = request.POST.get('isbn')
            libro.titulo = request.POST.get('titulo')
            libro.anio_publicacion = request.POST.get('anio_publicacion') or None
            libro.descripcion = request.POST.get('descripcion')
            libro.editorial_id = request.POST.get('editorial')
            libro.categoria_id = request.POST.get('categoria')
            libro.cantidad_total = cantidad_total
            libro.inventario_disponible = inventario_disponible
            libro.save()
            
            autores_ids = request.POST.getlist('autores')
            libro.autores.set(autores_ids)
            
            messages.success(request, f'✅ Libro "{libro.titulo}" actualizado exitosamente')
            return redirect('gestionar_libros')
            
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar libro: {str(e)}')
    
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
def libro_dar_baja(request, libro_id):
    """Dar de baja un libro (ocultar del catálogo)"""
    libro = get_object_or_404(Libro, id=libro_id)
    libro.activo = False
    libro.save()
    messages.success(request, f'✅ Libro "{libro.titulo}" dado de baja correctamente')
    return redirect('gestionar_libros')


@staff_member_required
def libro_dar_alta(request, libro_id):
    """Dar de alta un libro (mostrar en catálogo)"""
    libro = get_object_or_404(Libro, id=libro_id)
    libro.activo = True
    libro.save()
    messages.success(request, f'✅ Libro "{libro.titulo}" dado de alta correctamente')
    return redirect('gestionar_libros')


@staff_member_required
def gestionar_ejemplares(request, libro_id=None):
    """Gestionar ejemplares por libro"""
    if libro_id:
        libro = get_object_or_404(Libro, id=libro_id)
        ejemplares = Ejemplar.objects.filter(libro=libro).order_by('codigo_inventario')
    else:
        libro = None
        ejemplares = Ejemplar.objects.all().select_related('libro').order_by('libro__titulo', 'codigo_inventario')
    
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
            
            libro.cantidad_total = Ejemplar.objects.filter(libro=libro).count()
            libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
            libro.save()
            
            messages.success(request, f'✅ Ejemplar "{ejemplar.codigo_inventario}" agregado exitosamente')
            return redirect('gestionar_ejemplares_por_libro', libro_id=libro.id)
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear ejemplar: {str(e)}')
    
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
            
            libro = ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
            libro.save()
            
            messages.success(request, f'✅ Ejemplar "{ejemplar.codigo_inventario}" actualizado exitosamente')
            return redirect('gestionar_ejemplares_por_libro', libro_id=ejemplar.libro.id)
            
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar ejemplar: {str(e)}')
    
    context = {
        'ejemplar': ejemplar,
        'estado_fisico_choices': Ejemplar.ESTADO_FISICO_CHOICES,
        'disponibilidad_choices': Ejemplar.DISPONIBILIDAD_CHOICES,
    }
    return render(request, 'bibliotecario/ejemplar_form.html', context)


def detalle_libro(request, libro_id):
    """Vista para ver detalles de un libro específico"""
    libro = get_object_or_404(Libro, id=libro_id)
    ejemplares_disponibles = libro.ejemplares.filter(disponibilidad='DISPONIBLE')
    
    context = {
        'libro': libro,
        'ejemplares_disponibles': ejemplares_disponibles,
    }
    return render(request, 'catalogo/detalle.html', context)