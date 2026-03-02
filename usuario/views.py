from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Socio, NivelAcceso

# Vista para listar socios (solo personal autorizado)
@staff_member_required
def lista_socios(request):
    """Muestra la lista de todos los socios"""
    socios = Socio.objects.all().select_related('user', 'nivel_acceso')
    
    # Filtros básicos
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    
    if estado:
        socios = socios.filter(estado_socio=estado)
    if tipo:
        socios = socios.filter(tipo_usuario=tipo)
    
    context = {
        'socios': socios,
        'estados': Socio.ESTADO_SOCIO_CHOICES,
        'tipos': Socio.TIPO_USUARIO_CHOICES,
        'filtro_activo': estado or tipo
    }
    return render(request, 'usuario/socio_list.html', context)

# Vista para ver detalle de un socio
@staff_member_required
def detalle_socio(request, pk):
    """Muestra el detalle completo de un socio"""
    socio = get_object_or_404(Socio.objects.select_related('user', 'nivel_acceso'), pk=pk)
    
    context = {
        'socio': socio,
    }
    return render(request, 'usuario/socio_detail.html', context)

# Vista para crear nuevo socio (CORREGIDA)
@staff_member_required
def crear_socio(request):
    """Crea un nuevo socio (con usuario de Django automático)"""
    if request.method == 'POST':
        try:
            # Verificar que todos los campos requeridos están presentes
            campos_requeridos = ['cedula', 'email', 'nombre', 'apellido', 'tipo_usuario', 'nivel_acceso']
            for campo in campos_requeridos:
                if not request.POST.get(campo):
                    messages.error(request, f'El campo {campo} es obligatorio')
                    return redirect('crear_socio')
            
            # Crear usuario de Django primero
            username = request.POST.get('cedula')
            email = request.POST.get('email')
            password = request.POST.get('password', 'biblioteca2025')
            
            # Verificar si ya existe
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Ya existe un usuario con cédula {username}')
                return redirect('crear_socio')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, f'Ya existe un usuario con email {email}')
                return redirect('crear_socio')
            
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=request.POST.get('nombre'),
                last_name=request.POST.get('apellido')
            )
            
            # Crear socio vinculado
            socio = Socio.objects.create(
                user=user,
                cedula=request.POST.get('cedula'),
                telefono=request.POST.get('telefono', ''),
                direccion=request.POST.get('direccion', ''),
                carrera=request.POST.get('carrera', ''),
                tipo_usuario=request.POST.get('tipo_usuario'),
                estado_socio=request.POST.get('estado_socio', 'activo'),
                nivel_acceso_id=request.POST.get('nivel_acceso')
            )
            
            messages.success(request, f'✅ Socio {socio.nombre_completo} creado exitosamente')
            return redirect('detalle_socio', pk=socio.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear socio: {str(e)}')
            # Si se creó el usuario pero falló el socio, limpiar
            if 'user' in locals():
                user.delete()
            return redirect('crear_socio')
    
    # GET: mostrar formulario
    niveles = NivelAcceso.objects.all()
    context = {
        'niveles': niveles,
        'tipos_usuario': Socio.TIPO_USUARIO_CHOICES,
        'estados': Socio.ESTADO_SOCIO_CHOICES,
    }
    return render(request, 'usuario/socio_form.html', context)

# Vista para editar socio
@staff_member_required
def editar_socio(request, pk):
    """Edita un socio existente"""
    socio = get_object_or_404(Socio, pk=pk)
    
    if request.method == 'POST':
        try:
            # Actualizar datos del socio
            socio.telefono = request.POST.get('telefono')
            socio.direccion = request.POST.get('direccion')
            socio.carrera = request.POST.get('carrera')
            socio.tipo_usuario = request.POST.get('tipo_usuario')
            socio.estado_socio = request.POST.get('estado_socio')
            socio.nivel_acceso_id = request.POST.get('nivel_acceso')
            socio.save()
            
            # Actualizar usuario de Django
            socio.user.first_name = request.POST.get('nombre')
            socio.user.last_name = request.POST.get('apellido')
            socio.user.email = request.POST.get('email')
            socio.user.save()
            
            messages.success(request, f'Socio actualizado exitosamente')
            return redirect('detalle_socio', pk=socio.pk)
            
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
            return redirect('editar_socio', pk=socio.pk)
    
    # GET: mostrar formulario con datos actuales
    niveles = NivelAcceso.objects.all()
    context = {
        'socio': socio,
        'niveles': niveles,
        'tipos_usuario': Socio.TIPO_USUARIO_CHOICES,
        'estados': Socio.ESTADO_SOCIO_CHOICES,
    }
    return render(request, 'usuario/socio_form.html', context)

# Vista para eliminar socio
@staff_member_required
def eliminar_socio(request, pk):
    """Elimina un socio (o lo desactiva)"""
    socio = get_object_or_404(Socio, pk=pk)
    
    if request.method == 'POST':
        try:
            # Opción 2: Solo desactivar (recomendado)
            socio.estado_socio = 'inhabilitado'
            socio.user.is_active = False
            socio.user.save()
            socio.save()
            
            messages.success(request, f'Socio {socio.nombre_completo} ha sido inhabilitado')
            return redirect('lista_socios')
            
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('detalle_socio', pk=socio.pk)
    
    # GET: mostrar confirmación
    context = {'socio': socio}
    return render(request, 'usuario/socio_confirm_delete.html', context)

# Vista para buscar socios (CORREGIDA - email está en user)
@staff_member_required
def buscar_socios(request):
    """Búsqueda avanzada de socios"""
    query = request.GET.get('q', '')
    
    if query:
        socios = Socio.objects.filter(
            Q(cedula__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |  # Corregido: email está en user
            Q(carrera__icontains=query)
        ).select_related('user', 'nivel_acceso')
    else:
        socios = Socio.objects.none()
    
    context = {
        'socios': socios,
        'query': query,
        'resultados': socios.count()
    }
    return render(request, 'usuario/buscar_socios.html', context)