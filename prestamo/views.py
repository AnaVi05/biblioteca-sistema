from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from .models import Prestamo, Multa, Reserva
from catalogo.models import Ejemplar, Libro
from django.db.models import Count, Sum
from usuario.models import Socio 
from django.db import transaction


@staff_member_required
def lista_prestamos(request):
    """Lista todos los préstamos (para bibliotecarios)"""
    prestamos = Prestamo.objects.all().select_related('socio', 'ejemplar__libro')
    
    estado = request.GET.get('estado')
    if estado:
        prestamos = prestamos.filter(estado=estado)
    
    context = {
        'prestamos': prestamos,
        'estados': Prestamo.ESTADO_PRESTAMO_CHOICES,
        'hoy': date.today(),
    }
    return render(request, 'prestamo/lista.html', context)


@staff_member_required
def detalle_prestamo(request, pk):
    """Detalle de un préstamo"""
    prestamo = get_object_or_404(Prestamo.objects.select_related('socio', 'ejemplar__libro'), pk=pk)
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/detalle.html', context)


@staff_member_required
def crear_prestamo(request):
    """Vista para crear nuevo préstamo (seleccionar socio y ejemplar)"""
    if request.method == 'POST':
        messages.warning(request, 'Funcionalidad en desarrollo')
        return redirect('lista_prestamos')
    
    ejemplares_disponibles = Ejemplar.objects.filter(disponibilidad='DISPONIBLE')
    context = {'ejemplares': ejemplares_disponibles}
    return render(request, 'prestamo/crear_prestamo.html', context)


@staff_member_required
def devolver_prestamo(request, pk):
    """Registrar devolución de un préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if request.method == 'POST':
        prestamo.fecha_devolucion_real = date.today()
        prestamo.estado = 'DEVUELTO'
        prestamo.save()
        
        # Actualizar disponibilidad del ejemplar
        if prestamo.ejemplar:
            prestamo.ejemplar.disponibilidad = 'DISPONIBLE'
            prestamo.ejemplar.save()
            
            # Actualizar inventario del libro
            libro = prestamo.ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(
                libro=libro, 
                disponibilidad='DISPONIBLE'
            ).count()
            libro.save()
        
        # Calcular atraso y posible multa
        dias_atraso = prestamo.dias_atraso
        if dias_atraso > 0:
            Multa.objects.create(
                prestamo=prestamo,
                dias_atraso=dias_atraso,
                monto_base=5000.00,
                monto_por_dia=5000.00,
                monto_total=dias_atraso * 5000.00
            )
            messages.warning(request, f'Préstamo devuelto con {dias_atraso} días de atraso. Multa generada.')
        else:
            messages.success(request, 'Préstamo devuelto exitosamente')
        
        return redirect('detalle_prestamo', pk=prestamo.pk)
    
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/devolver.html', context)


@staff_member_required
def marcar_extraviado(request, pk):
    """Marca un préstamo como extraviado"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        prestamo.marcar_extraviado(observaciones)
        messages.warning(request, f'Préstamo marcado como EXTRAVIADO. Se generó multa especial.')
        return redirect('detalle_prestamo', pk=prestamo.pk)
    
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/marcar_extraviado.html', context)


# ========== VISTAS PARA USUARIOS ==========

@login_required
def registrar_prestamo_usuario(request, ejemplar_id):
    """Usuario registra su propio préstamo (desde catálogo)"""
    try:
        ejemplar = Ejemplar.objects.get(id=ejemplar_id)
    except Ejemplar.DoesNotExist:
        messages.error(request, f'El ejemplar con ID {ejemplar_id} no existe')
        return redirect('catalogo_lista')
    
    if ejemplar.disponibilidad.upper() != 'DISPONIBLE':
        messages.error(request, f'El ejemplar {ejemplar.codigo_inventario} no está disponible')
        return redirect('catalogo_lista')
    
    if request.method == 'POST':
        try:
            dias_solicitados = int(request.POST.get('dias_solicitados'))
        except (TypeError, ValueError):
            messages.error(request, 'Debés seleccionar una cantidad de días válida')
            return redirect('registrar_prestamo_usuario', ejemplar_id=ejemplar.id)
        
        if dias_solicitados < 1 or dias_solicitados > 5:
            messages.error(request, 'Los días deben ser entre 1 y 5')
            return redirect('registrar_prestamo_usuario', ejemplar_id=ejemplar.id)
        
        # Crear préstamo
        prestamo = Prestamo.objects.create(
            socio=request.user.socio,
            ejemplar=ejemplar,
            dias_solicitados=dias_solicitados,
            fecha_prestamo=timezone.now(),
            fecha_vencimiento=date.today() + timedelta(days=dias_solicitados),
            estado='ACTIVO'
        )
        
        # Actualizar disponibilidad del ejemplar
        ejemplar.disponibilidad = 'PRESTADO'
        ejemplar.save()
        
        # Actualizar inventario del libro
        libro = ejemplar.libro
        libro.inventario_disponible = Ejemplar.objects.filter(
            libro=libro, 
            disponibilidad='DISPONIBLE'
        ).count()
        libro.save()
        
        messages.success(request, f'✅ Préstamo registrado. Devolver antes del {prestamo.fecha_vencimiento.strftime("%d/%m/%Y")}')
        return redirect('mis_prestamos')
    
    context = {
        'ejemplar': ejemplar,
        'max_dias': 5
    }
    return render(request, 'prestamo/registrar_prestamo.html', context)


@login_required
def mis_prestamos(request):
    """Vista para que el usuario vea sus préstamos"""
    prestamos = Prestamo.objects.filter(
        socio=request.user.socio
    ).select_related('ejemplar__libro').order_by('-fecha_prestamo')
    
    # Separar activos y devueltos
    prestamos_activos = prestamos.filter(estado__in=['ACTIVO', 'VENCIDO'])
    historial = prestamos.filter(estado__in=['DEVUELTO', 'EXTRAVIADO'])
    
    context = {
        'activos': prestamos_activos,
        'historial': historial,
        'hoy': date.today(),
    }
    return render(request, 'prestamo/mis_prestamos.html', context)


@login_required
def devolver_prestamo_usuario(request, prestamo_id):
    """Usuario confirma devolución de su préstamo"""
    prestamo = get_object_or_404(Prestamo, id=prestamo_id, socio=request.user.socio, estado='ACTIVO')
    
    if request.method == 'POST':
        prestamo.fecha_devolucion_real = date.today()
        prestamo.estado = 'DEVUELTO'
        prestamo.save()
        
        # Actualizar ejemplar
        if prestamo.ejemplar:
            prestamo.ejemplar.disponibilidad = 'DISPONIBLE'
            prestamo.ejemplar.save()
            
            # Actualizar inventario del libro
            libro = prestamo.ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(
                libro=libro, 
                disponibilidad='DISPONIBLE'
            ).count()
            libro.save()
        
        # Verificar atraso
        dias_atraso = prestamo.dias_atraso
        if dias_atraso > 0:
            Multa.objects.create(
                prestamo=prestamo,
                dias_atraso=dias_atraso,
                monto_base=5000.00,
                monto_por_dia=5000.00,
                monto_total=dias_atraso * 5000.00
            )
            messages.warning(request, f'Libro devuelto con {dias_atraso} días de atraso. Se generó una multa.')
        else:
            messages.success(request, '¡Gracias por devolver el libro!')
        
        return redirect('mis_prestamos')
    
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/confirmar_devolucion.html', context)


# ========== VISTAS PARA RESERVAS ==========

@login_required
def reservar_libro(request, libro_id):
    """Permite al usuario reservar un libro no disponible"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    # Verificar si hay ejemplares disponibles
    ejemplares_disponibles = Ejemplar.objects.filter(
        libro=libro, 
        disponibilidad='DISPONIBLE'
    ).count()
    
    if ejemplares_disponibles > 0:
        messages.info(request, 'Este libro tiene ejemplares disponibles. ¿Querés solicitarlo en préstamo?')
        return redirect('catalogo_lista')
    
    if request.method == 'POST':
        fecha_limite = request.POST.get('fecha_limite_interes')
        
        try:
            fecha_limite_date = date.fromisoformat(fecha_limite)
        except ValueError:
            messages.error(request, 'Fecha inválida')
            return redirect('reservar_libro', libro_id=libro.id)
        
        # Validar fecha límite
        fecha_min = date.today() + timedelta(days=1)
        fecha_max = date.today() + timedelta(days=30)
        
        if fecha_limite_date < fecha_min:
            messages.error(request, 'La fecha límite debe ser al menos mañana')
            return redirect('reservar_libro', libro_id=libro.id)
        
        if fecha_limite_date > fecha_max:
            messages.error(request, 'La fecha límite no puede ser mayor a 30 días')
            return redirect('reservar_libro', libro_id=libro.id)
        
        # Verificar si ya tiene una reserva activa
        reserva_existente = Reserva.objects.filter(
            socio=request.user.socio,
            libro=libro,
            estado__in=['PENDIENTE', 'ACTIVA']
        ).exists()
        
        if reserva_existente:
            messages.warning(request, 'Ya tenés una reserva activa para este libro')
            return redirect('mis_reservas')
        
        # Calcular posición en cola
        ultima_posicion = Reserva.objects.filter(
            libro=libro,
            estado__in=['PENDIENTE', 'ACTIVA']
        ).count()
        
        # Crear reserva
        reserva = Reserva.objects.create(
            socio=request.user.socio,
            libro=libro,
            fecha_expiracion=fecha_limite_date,
            orden_prioridad=ultima_posicion + 1,
            estado='PENDIENTE'
        )
        
        messages.success(
            request, 
            f'✅ ¡Libro reservado! Estás en la posición {reserva.orden_prioridad} de la cola.'
        )
        return redirect('mis_reservas')
    
    fecha_min = date.today() + timedelta(days=1)
    fecha_max = date.today() + timedelta(days=30)
    
    context = {
        'libro': libro,
        'fecha_min': fecha_min.isoformat(),
        'fecha_max': fecha_max.isoformat(),
        'ejemplares_disponibles': ejemplares_disponibles
    }
    return render(request, 'prestamo/reservar_libro.html', context)


@login_required
def mis_reservas(request):
    """Lista las reservas del usuario"""
    reservas_activas = Reserva.objects.filter(
        socio=request.user.socio,
        estado__in=['PENDIENTE', 'ACTIVA']
    ).select_related('libro').order_by('orden_prioridad', 'fecha_reserva')
    
    historial = Reserva.objects.filter(
        socio=request.user.socio,
        estado__in=['CANCELADA', 'COMPLETADA', 'EXPIRADA']
    ).select_related('libro').order_by('-fecha_reserva')[:10]
    
    context = {
        'reservas_activas': reservas_activas,
        'historial': historial,
        'hoy': date.today()
    }
    return render(request, 'prestamo/mis_reservas.html', context)


@login_required
def cancelar_reserva(request, reserva_id):
    """Cancela una reserva activa"""
    reserva = get_object_or_404(
        Reserva, 
        id=reserva_id, 
        socio=request.user.socio,
        estado='PENDIENTE'
    )
    
    if request.method == 'POST':
        reserva.estado = 'CANCELADA'
        reserva.save()
        messages.success(request, 'Reserva cancelada exitosamente')
        return redirect('mis_reservas')
    
    context = {'reserva': reserva}
    return render(request, 'prestamo/cancelar_reserva.html', context)


# ========== #panel bibliotecario

@staff_member_required
def dashboard_bibliotecario(request):
    """
    
    Dashboard principal para bibliotecarios
    """
    hoy = timezone.now().date()
    
    # ========== ESTADÍSTICAS PRINCIPALES ==========
    
    # Préstamos activos
    prestamos_activos = Prestamo.objects.filter(
        estado='ACTIVO'
    ).count()
    
    # Préstamos del día (registrados hoy)
    prestamos_hoy = Prestamo.objects.filter(
        fecha_prestamo__date=hoy
    ).count()
    
    # Préstamos vencidos
    prestamos_vencidos = Prestamo.objects.filter(
        estado='ACTIVO',
        fecha_vencimiento__lt=hoy
    ).count()
    
    # Devoluciones pendientes (préstamos activos vencidos)
    devoluciones_pendientes = prestamos_vencidos
    
    # Ejemplares disponibles
    from catalogo.models import Ejemplar
    ejemplares_disponibles = Ejemplar.objects.filter(
        disponibilidad='DISPONIBLE'
    ).count()
    
    # Reservas pendientes
    reservas_pendientes = Reserva.objects.filter(
        estado='PENDIENTE',
        fecha_expiracion__date__gte=hoy
    ).count()
    
    # Reservas activas
    reservas_activas = reservas_pendientes
    
    # Total de multas pendientes
    total_multas_pendientes = Multa.objects.filter(
        estado='PENDIENTE'
    ).aggregate(
        total=Sum('monto_total')
    )['total'] or 0
    
    # Usuarios con multas pendientes
    usuarios_morosos = Multa.objects.filter(
        estado='PENDIENTE'
    ).values('prestamo__socio').distinct().count()
    
    total_morosos = usuarios_morosos
    
    # Socios activos
    from usuario.models import Socio
    socios_activos = Socio.objects.filter(
        estado_socio='activo'
    ).count()
    
    # Préstamos próximos a vencer (próximos 3 días)
    proximos_a_vencer = Prestamo.objects.filter(
        estado='ACTIVO',
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=3)
    ).count()
    
    # ========== TAREAS PENDIENTES (datos reales) ==========
    tareas_pendientes = []
    
    # Agregar préstamos vencidos como tareas
    prestamos_vencidos_lista = Prestamo.objects.filter(
        estado='ACTIVO',
        fecha_vencimiento__lt=hoy
    ).select_related('socio__user', 'ejemplar__libro')[:3]
    
    for prestamo in prestamos_vencidos_lista:
        tareas_pendientes.append({
            'titulo': 'Devolución atrasada',
            'descripcion': f"{prestamo.socio.user.get_full_name()} - \"{prestamo.ejemplar.libro.titulo}\""
        })
    
    # Agregar usuarios con multas como tareas
    multas_pendientes = Multa.objects.filter(
        estado='PENDIENTE'
    ).select_related('prestamo__socio__user')[:2]
    
    for multa in multas_pendientes:
        tareas_pendientes.append({
            'titulo': 'Usuario con multa',
            'descripcion': f"{multa.prestamo.socio.user.get_full_name()} - Gs. {multa.monto_total:,.0f} pendientes"
        })
    
    # Agregar reservas pendientes como tareas
    reservas_lista = Reserva.objects.filter(
        estado='PENDIENTE',
        fecha_expiracion__date__gte=hoy
    ).select_related('socio__user', 'libro')[:2]
    
    for reserva in reservas_lista:
        tareas_pendientes.append({
            'titulo': 'Reserva por confirmar',
            'descripcion': f"{reserva.socio.user.get_full_name()} - \"{reserva.libro.titulo}\""
        })
    
    # ========== ACTIVIDAD RECIENTE ==========
    actividades_recientes = []
    
    # Últimos préstamos
    ultimos_prestamos = Prestamo.objects.select_related(
        'socio__user', 'ejemplar__libro'
    ).order_by('-fecha_prestamo')[:2]
    
    for prestamo in ultimos_prestamos:
        actividades_recientes.append({
            'titulo': 'Préstamo registrado',
            'descripcion': f"{prestamo.socio.user.get_full_name()} - \"{prestamo.ejemplar.libro.titulo}\""
        })
    
    # Últimas devoluciones
    ultimas_devoluciones = Prestamo.objects.filter(
        fecha_devolucion_real__isnull=False
    ).select_related(
        'socio__user', 'ejemplar__libro'
    ).order_by('-fecha_devolucion_real')[:2]
    
    for devolucion in ultimas_devoluciones:
        actividades_recientes.append({
            'titulo': 'Devolución procesada',
            'descripcion': f"{devolucion.socio.user.get_full_name()} - \"{devolucion.ejemplar.libro.titulo}\""
        })
    
    # Últimas reservas confirmadas
    reservas_confirmadas = Reserva.objects.filter(
        estado='COMPLETADA'
    ).select_related('socio__user', 'libro').order_by('-fecha_reserva')[:1]
    
    for reserva in reservas_confirmadas:
        actividades_recientes.append({
            'titulo': 'Reserva confirmada',
            'descripcion': f"{reserva.socio.user.get_full_name()} - \"{reserva.libro.titulo}\""
        })
    
    context = {
        # Estadísticas principales
        'prestamos_activos': prestamos_activos,
        'prestamos_hoy': prestamos_hoy,
        'prestamos_vencidos': prestamos_vencidos,
        'devoluciones_pendientes': devoluciones_pendientes,
        'ejemplares_disponibles': ejemplares_disponibles,
        'reservas_pendientes': reservas_pendientes,
        'reservas_activas': reservas_activas,
        'total_multas_pendientes': total_multas_pendientes,
        'usuarios_morosos': usuarios_morosos,
        'total_morosos': total_morosos,
        'socios_activos': socios_activos,
        'proximos_a_vencer': proximos_a_vencer,
        
        # Tareas y actividades
        'tareas_pendientes': tareas_pendientes,
        'actividades_recientes': actividades_recientes,
    }
    
    return render(request, 'bibliotecario/dashboard.html', context)
         

@staff_member_required
def prestamo_nuevo_bibliotecario(request):
    """
    Registrar un nuevo préstamo desde el panel bibliotecario
    """
    from django.contrib import messages
    from django.db import transaction
    from django.utils import timezone
    from datetime import timedelta
    
    # Obtener parámetros de búsqueda
    socio_cedula = request.GET.get('socio_cedula', '')
    socio_nombre = request.GET.get('socio_nombre', '')
    ejemplar_codigo = request.GET.get('ejemplar_codigo', '')
    ejemplar_titulo = request.GET.get('ejemplar_titulo', '')
    
    socio_seleccionado = None
    ejemplar_seleccionado = None
    
    # Búsqueda de socio
    socios = []
    if socio_cedula or socio_nombre:
        socios = Socio.objects.filter(estado_socio='activo')
        if socio_cedula:
            socios = socios.filter(cedula__icontains=socio_cedula)
        if socio_nombre:
            socios = socios.filter(
                user__first_name__icontains=socio_nombre
            ) | socios.filter(
                user__last_name__icontains=socio_nombre
            )
        socios = socios[:10]
    
    # Búsqueda de ejemplares disponibles
    ejemplares = []
    if ejemplar_codigo or ejemplar_titulo:
        ejemplares = Ejemplar.objects.filter(
            disponibilidad='DISPONIBLE'
        ).select_related('libro')
        
        if ejemplar_codigo:
            ejemplares = ejemplares.filter(codigo_inventario__icontains=ejemplar_codigo)
        if ejemplar_titulo:
            ejemplares = ejemplares.filter(libro__titulo__icontains=ejemplar_titulo)
        ejemplares = ejemplares[:10]
    
    # Si se seleccionó un socio via GET
    socio_id = request.GET.get('socio_id')
    if socio_id:
        try:
            socio_seleccionado = Socio.objects.get(id=socio_id)
        except Socio.DoesNotExist:
            pass
    
    # Si se seleccionó un ejemplar via GET
    ejemplar_id = request.GET.get('ejemplar_id')
    if ejemplar_id:
        try:
            ejemplar_seleccionado = Ejemplar.objects.get(id=ejemplar_id)
        except Ejemplar.DoesNotExist:
            pass
    
    # Procesar el formulario cuando se envía
    if request.method == 'POST':
        socio_id = request.POST.get('socio_id')
        ejemplar_id = request.POST.get('ejemplar_id')
        dias = int(request.POST.get('dias_solicitados', 3))
        
        if not socio_id or not ejemplar_id:
            messages.error(request, 'Debe seleccionar un socio y un ejemplar')
        elif dias < 1 or dias > 5:
            messages.error(request, 'Los días de préstamo deben ser entre 1 y 5')
        else:
            try:
                with transaction.atomic():
                    socio = Socio.objects.get(id=socio_id)
                    ejemplar = Ejemplar.objects.get(id=ejemplar_id)
                    
                    # Verificar que el ejemplar siga disponible
                    if ejemplar.disponibilidad != 'DISPONIBLE':
                        messages.error(request, 'El ejemplar ya no está disponible')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
                    # Verificar que el socio no tenga multas pendientes
                    tiene_multas = Multa.objects.filter(
                        prestamo__socio=socio,
                        estado='PENDIENTE'
                    ).exists()
                    
                    if tiene_multas:
                        messages.warning(request, 'El socio tiene multas pendientes')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
                    # Crear el préstamo
                    fecha_prestamo = timezone.now()
                    fecha_vencimiento = fecha_prestamo.date() + timedelta(days=dias)
                    
                    prestamo = Prestamo.objects.create(
                        socio=socio,
                        ejemplar=ejemplar,
                        dias_solicitados=dias,
                        fecha_prestamo=fecha_prestamo,
                        fecha_vencimiento=fecha_vencimiento,
                        estado='ACTIVO'
                    )
                    
                    # Actualizar disponibilidad del ejemplar
                    ejemplar.disponibilidad = 'PRESTADO'
                    ejemplar.save()
                    
                    messages.success(request, f'Préstamo #{prestamo.id} registrado exitosamente')
                    return redirect('dashboard_bibliotecario')
                    
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    
    context = {
        'socios': socios,
        'ejemplares': ejemplares,
        'socio_seleccionado': socio_seleccionado,
        'ejemplar_seleccionado': ejemplar_seleccionado,
        'socio_cedula': socio_cedula,
        'socio_nombre': socio_nombre,
        'ejemplar_codigo': ejemplar_codigo,
        'ejemplar_titulo': ejemplar_titulo,
    }
    
    return render(request, 'bibliotecario/prestamo_nuevo.html', context)

    # ========== VISTAS PLACEHOLDER (en desarrollo) ==========

@staff_member_required
def registrar_devolucion(request):
    """Vista temporal - Registrar devolución"""
    return render(request, 'bibliotecario/en_construccion.html', {
        'titulo': 'Registrar Devolución',
        'mensaje': 'Próximamente: Sistema de registro de devoluciones con cálculo de multas'
    })

@staff_member_required
def gestionar_reservas(request):
    """Vista temporal - Gestionar reservas"""
    return render(request, 'bibliotecario/en_construccion.html', {
        'titulo': 'Gestionar Reservas',
        'mensaje': 'Próximamente: Gestión de reservas y sistema de cola de espera'
    })

@staff_member_required
def gestionar_multas(request):
    """Vista temporal - Gestionar multas y morosos"""
    return render(request, 'bibliotecario/en_construccion.html', {
        'titulo': 'Usuarios Morosos',
        'mensaje': 'Próximamente: Gestión de multas y registro de pagos'
    })



    
    
   
       
