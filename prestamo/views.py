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
    """Registrar devolución de un préstamo (desde detalle)"""
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
        
        # Crear préstamo en estado SOLICITADO
        prestamo = Prestamo.objects.create(
            socio=request.user.socio,
            ejemplar=ejemplar,
            dias_solicitados=dias_solicitados,
            fecha_prestamo=timezone.now(),
            fecha_vencimiento=date.today() + timedelta(days=dias_solicitados),
            estado='SOLICITADO'   
        )
        
        messages.success(request, f'✅ Solicitud de préstamo enviada. Esperá confirmación del bibliotecario.')
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
    
    prestamos_activos = prestamos.filter(estado='ACTIVO')
    prestamos_solicitados = prestamos.filter(estado='SOLICITADO')
    historial = prestamos.filter(estado__in=['DEVUELTO', 'EXTRAVIADO'])
    
    context = {
        'activos': prestamos_activos,
        'solicitados': prestamos_solicitados,
        'historial': historial,
        'hoy': date.today(),
    }
    return render(request, 'prestamo/mis_prestamos.html', context)


@login_required
def devolver_prestamo_usuario(request, prestamo_id):
    """Usuario confirma devolución de su préstamo (YA NO SE USA)"""
    prestamo = get_object_or_404(Prestamo, id=prestamo_id, socio=request.user.socio, estado='ACTIVO')
    
    if request.method == 'POST':
        prestamo.fecha_devolucion_real = date.today()
        prestamo.estado = 'DEVUELTO'
        prestamo.save()
        
        if prestamo.ejemplar:
            prestamo.ejemplar.disponibilidad = 'DISPONIBLE'
            prestamo.ejemplar.save()
            
            libro = prestamo.ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(
                libro=libro, 
                disponibilidad='DISPONIBLE'
            ).count()
            libro.save()
        
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


@login_required
def cancelar_solicitud(request, prestamo_id):
    """Cancela una solicitud de préstamo (estado SOLICITADO)"""
    prestamo = get_object_or_404(
        Prestamo, 
        id=prestamo_id, 
        socio=request.user.socio,
        estado='SOLICITADO'
    )
    
    if request.method == 'POST':
        prestamo.estado = 'CANCELADA'  
        prestamo.save()
        messages.success(request, 'Solicitud de préstamo cancelada exitosamente')
        return redirect('mis_prestamos')
    
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/cancelar_solicitud.html', context)


# ========== VISTAS PARA RESERVAS ==========

@login_required
def reservar_libro(request, libro_id):
    """Permite al usuario reservar un libro no disponible"""
    libro = get_object_or_404(Libro, id=libro_id)
    
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
        
        fecha_min = date.today() + timedelta(days=1)
        fecha_max = date.today() + timedelta(days=30)
        
        if fecha_limite_date < fecha_min:
            messages.error(request, 'La fecha límite debe ser al menos mañana')
            return redirect('reservar_libro', libro_id=libro.id)
        
        if fecha_limite_date > fecha_max:
            messages.error(request, 'La fecha límite no puede ser mayor a 30 días')
            return redirect('reservar_libro', libro_id=libro.id)
        
        reserva_existente = Reserva.objects.filter(
            socio=request.user.socio,
            libro=libro,
            estado__in=['PENDIENTE', 'ACTIVA']
        ).exists()
        
        if reserva_existente:
            messages.warning(request, 'Ya tenés una reserva activa para este libro')
            return redirect('mis_reservas')
        
        ultima_posicion = Reserva.objects.filter(
            libro=libro,
            estado__in=['PENDIENTE', 'ACTIVA']
        ).count()
        
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
        reserva.delete()
        messages.success(request, 'Reserva cancelada exitosamente')
        return redirect('mis_reservas')
    
    context = {'reserva': reserva}
    return render(request, 'prestamo/cancelar_reserva.html', context)


# ========== PANEL BIBLIOTECARIO ==========

@staff_member_required
def dashboard_bibliotecario(request):
    """Dashboard principal para bibliotecarios"""
    hoy = timezone.now().date()
    
    # Estadísticas
    prestamos_activos = Prestamo.objects.filter(estado='ACTIVO').count()
    prestamos_hoy = Prestamo.objects.filter(fecha_prestamo__date=hoy).count()
    prestamos_vencidos = Prestamo.objects.filter(estado='ACTIVO', fecha_vencimiento__lt=hoy).count()
    devoluciones_pendientes = prestamos_vencidos
    ejemplares_disponibles = Ejemplar.objects.filter(disponibilidad='DISPONIBLE').count()
    reservas_pendientes = Reserva.objects.filter(estado='PENDIENTE', fecha_expiracion__date__gte=hoy).count()
    total_multas_pendientes = Multa.objects.filter(estado='PENDIENTE').aggregate(total=Sum('monto_total'))['total'] or 0
    usuarios_morosos = Multa.objects.filter(estado='PENDIENTE').values('prestamo__socio').distinct().count()
    socios_activos = Socio.objects.filter(estado_socio='activo').count()
    proximos_a_vencer = Prestamo.objects.filter(
        estado='ACTIVO',
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=3)
    ).count()
    
    solicitudes_pendientes = Prestamo.objects.filter(
        estado='SOLICITADO'
    ).select_related('socio__user', 'ejemplar__libro').order_by('fecha_prestamo')
    
    # Tareas pendientes
    tareas_pendientes = []
    
    for prestamo in Prestamo.objects.filter(estado='ACTIVO', fecha_vencimiento__lt=hoy).select_related('socio__user', 'ejemplar__libro')[:3]:
        tareas_pendientes.append({
            'titulo': 'Devolución atrasada',
            'descripcion': f"{prestamo.socio.user.get_full_name()} - \"{prestamo.ejemplar.libro.titulo}\""
        })
    
    for multa in Multa.objects.filter(estado='PENDIENTE').select_related('prestamo__socio__user')[:2]:
        tareas_pendientes.append({
            'titulo': 'Usuario con multa',
            'descripcion': f"{multa.prestamo.socio.user.get_full_name()} - Gs. {multa.monto_total:,.0f} pendientes"
        })
    
    for reserva in Reserva.objects.filter(estado='PENDIENTE', fecha_expiracion__date__gte=hoy).select_related('socio__user', 'libro')[:2]:
        tareas_pendientes.append({
            'titulo': 'Reserva por confirmar',
            'descripcion': f"{reserva.socio.user.get_full_name()} - \"{reserva.libro.titulo}\""
        })
    
    # Actividad reciente
    actividades_recientes = []
    
    for prestamo in Prestamo.objects.select_related('socio__user', 'ejemplar__libro').order_by('-fecha_prestamo')[:2]:
        actividades_recientes.append({
            'titulo': 'Préstamo registrado',
            'descripcion': f"{prestamo.socio.user.get_full_name()} - \"{prestamo.ejemplar.libro.titulo}\""
        })
    
    for devolucion in Prestamo.objects.filter(fecha_devolucion_real__isnull=False).select_related('socio__user', 'ejemplar__libro').order_by('-fecha_devolucion_real')[:2]:
        actividades_recientes.append({
            'titulo': 'Devolución procesada',
            'descripcion': f"{devolucion.socio.user.get_full_name()} - \"{devolucion.ejemplar.libro.titulo}\""
        })
    
    for reserva in Reserva.objects.filter(estado='COMPLETADA').select_related('socio__user', 'libro').order_by('-fecha_reserva')[:1]:
        actividades_recientes.append({
            'titulo': 'Reserva confirmada',
            'descripcion': f"{reserva.socio.user.get_full_name()} - \"{reserva.libro.titulo}\""
        })
    
    context = {
        'prestamos_activos': prestamos_activos,
        'prestamos_hoy': prestamos_hoy,
        'prestamos_vencidos': prestamos_vencidos,
        'devoluciones_pendientes': devoluciones_pendientes,
        'ejemplares_disponibles': ejemplares_disponibles,
        'reservas_pendientes': reservas_pendientes,
        'total_multas_pendientes': total_multas_pendientes,
        'usuarios_morosos': usuarios_morosos,
        'total_morosos': usuarios_morosos,
        'socios_activos': socios_activos,
        'proximos_a_vencer': proximos_a_vencer,
        'solicitudes_pendientes': solicitudes_pendientes,
        'tareas_pendientes': tareas_pendientes,
        'actividades_recientes': actividades_recientes,
    }
    
    return render(request, 'bibliotecario/dashboard.html', context)


@staff_member_required
def confirmar_prestamo(request, prestamo_id):
    """Confirmar entrega de un préstamo solicitado"""
    try:
        prestamo = Prestamo.objects.get(id=prestamo_id, estado='SOLICITADO')
    except Prestamo.DoesNotExist:
        messages.error(request, 'Solicitud de préstamo no encontrada')
        return redirect('dashboard_bibliotecario')
    
    if request.method == 'POST':
        with transaction.atomic():
            prestamo.estado = 'ACTIVO'
            prestamo.save()
            
            ejemplar = prestamo.ejemplar
            ejemplar.disponibilidad = 'PRESTADO'
            ejemplar.save()
            
            libro = ejemplar.libro
            libro.inventario_disponible = Ejemplar.objects.filter(
                libro=libro, 
                disponibilidad='DISPONIBLE'
            ).count()
            libro.save()
            
            messages.success(request, f'✅ Préstamo confirmado. Libro entregado a {prestamo.socio.user.get_full_name()}')
            
        return redirect('dashboard_bibliotecario')
    
    context = {'prestamo': prestamo}
    return render(request, 'bibliotecario/confirmar_prestamo.html', context)


@staff_member_required
def prestamo_nuevo_bibliotecario(request):
    """Registrar un nuevo préstamo desde el panel bibliotecario"""
    socio_cedula = request.GET.get('socio_cedula', '')
    socio_nombre = request.GET.get('socio_nombre', '')
    ejemplar_codigo = request.GET.get('ejemplar_codigo', '')
    ejemplar_titulo = request.GET.get('ejemplar_titulo', '')
    
    socio_seleccionado = None
    ejemplar_seleccionado = None
    
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
    
    ejemplares = []
    if ejemplar_codigo or ejemplar_titulo:
        ejemplares = Ejemplar.objects.filter(disponibilidad='DISPONIBLE').select_related('libro')
        if ejemplar_codigo:
            ejemplares = ejemplares.filter(codigo_inventario__icontains=ejemplar_codigo)
        if ejemplar_titulo:
            ejemplares = ejemplares.filter(libro__titulo__icontains=ejemplar_titulo)
        ejemplares = ejemplares[:10]
    
    socio_id = request.GET.get('socio_id')
    if socio_id:
        try:
            socio_seleccionado = Socio.objects.get(id=socio_id)
        except Socio.DoesNotExist:
            pass
    
    ejemplar_id = request.GET.get('ejemplar_id')
    if ejemplar_id:
        try:
            ejemplar_seleccionado = Ejemplar.objects.get(id=ejemplar_id)
        except Ejemplar.DoesNotExist:
            pass
    
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
                    
                    if ejemplar.disponibilidad != 'DISPONIBLE':
                        messages.error(request, 'El ejemplar ya no está disponible')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
                    tiene_multas = Multa.objects.filter(
                        prestamo__socio=socio,
                        estado='PENDIENTE'
                    ).exists()
                    
                    if tiene_multas:
                        messages.warning(request, 'El socio tiene multas pendientes')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
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


# ========== REGISTRAR DEVOLUCIÓN (PRINCIPAL) ==========
@staff_member_required
def registrar_devolucion(request):
    """Registrar devolución de un préstamo desde el panel"""
    from decimal import Decimal
    
    prestamos_activos = Prestamo.objects.filter(
        estado='ACTIVO'
    ).select_related(
        'socio__user', 'ejemplar__libro'
    ).order_by('fecha_vencimiento')
    
    search = request.GET.get('search', '')
    if search:
        prestamos_activos = prestamos_activos.filter(
            socio__user__first_name__icontains=search
        ) | prestamos_activos.filter(
            socio__user__last_name__icontains=search
        ) | prestamos_activos.filter(
            ejemplar__libro__titulo__icontains=search
        ) | prestamos_activos.filter(
            ejemplar__codigo_inventario__icontains=search
        )
    
    prestamo_id = request.GET.get('devolver_id')
    prestamo_seleccionado = None
    multa_calculada = None
    
    if prestamo_id:
        try:
            prestamo_seleccionado = Prestamo.objects.select_related(
                'socio__user', 'ejemplar__libro'
            ).get(id=prestamo_id, estado='ACTIVO')
            
            hoy = timezone.now().date()
            if prestamo_seleccionado.fecha_vencimiento < hoy:
                dias_atraso = (hoy - prestamo_seleccionado.fecha_vencimiento).days
                monto_por_dia = Decimal('1000')
                monto_total = dias_atraso * monto_por_dia
                multa_calculada = {
                    'dias_atraso': dias_atraso,
                    'monto_por_dia': monto_por_dia,
                    'monto_total': monto_total
                }
        except Prestamo.DoesNotExist:
            pass
    
    if request.method == 'POST':
        prestamo_id = request.POST.get('prestamo_id')
        
        try:
            with transaction.atomic():
                prestamo = Prestamo.objects.select_related(
                    'socio', 'ejemplar'
                ).get(id=prestamo_id, estado='ACTIVO')
                
                hoy = timezone.now().date()
                dias_atraso = 0
                monto_multa = Decimal('0')
                
                if prestamo.fecha_vencimiento < hoy:
                    dias_atraso = (hoy - prestamo.fecha_vencimiento).days
                    monto_por_dia = Decimal('1000')
                    monto_multa = dias_atraso * monto_por_dia
                
                prestamo.fecha_devolucion_real = hoy
                prestamo.estado = 'DEVUELTO'
                prestamo.save()
                
                # ✅ ACTUALIZAR DISPONIBILIDAD DEL EJEMPLAR
                prestamo.ejemplar.disponibilidad = 'DISPONIBLE'
                prestamo.ejemplar.save()
                
                # ✅ ACTUALIZAR INVENTARIO DEL LIBRO
                libro = prestamo.ejemplar.libro
                libro.inventario_disponible = Ejemplar.objects.filter(
                    libro=libro, 
                    disponibilidad='DISPONIBLE'
                ).count()
                libro.save()
                
                if dias_atraso > 0:
                    Multa.objects.create(
                        prestamo=prestamo,
                        dias_atraso=dias_atraso,
                        monto_base=monto_por_dia,
                        monto_por_dia=monto_por_dia,
                        monto_total=monto_multa,
                        fecha_generacion=hoy,
                        estado='PENDIENTE'
                    )
                    messages.warning(request, f'Devolución registrada. Multa generada: Gs. {monto_multa:,.0f} por {dias_atraso} días de atraso.')
                else:
                    messages.success(request, f'Devolución registrada exitosamente.')
                
                return redirect('registrar_devolucion')
                
        except Prestamo.DoesNotExist:
            messages.error(request, 'Préstamo no encontrado')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'prestamos_activos': prestamos_activos,
        'search': search,
        'prestamo_seleccionado': prestamo_seleccionado,
        'multa_calculada': multa_calculada,
        'hoy': timezone.now().date(),
    }
    
    return render(request, 'bibliotecario/devolucion.html', context)


@staff_member_required
def gestionar_reservas(request):
    """Gestionar reservas de libros"""
    try:
        accion = request.GET.get('accion')
        reserva_id = request.GET.get('reserva_id')
        search = request.GET.get('search', '')
        
        if accion and reserva_id:
            try:
                reserva = Reserva.objects.select_related('socio', 'libro', 'ejemplar_asignado').get(id=reserva_id)
                
                if accion == 'confirmar':
                    with transaction.atomic():
                        ejemplar_disponible = Ejemplar.objects.filter(
                            libro=reserva.libro,
                            disponibilidad='DISPONIBLE'
                        ).first()
                        
                        if ejemplar_disponible:
                            reserva.estado = 'ACTIVA'
                            reserva.ejemplar_asignado = ejemplar_disponible
                            reserva.save()
                            
                            ejemplar_disponible.disponibilidad = 'RESERVADO'
                            ejemplar_disponible.save()
                            
                            messages.success(request, f'Reserva #{reserva.id} confirmada.')
                        else:
                            messages.warning(request, f'No hay ejemplares disponibles')
                            
                elif accion == 'cancelar':
                    reserva.estado = 'CANCELADA'
                    reserva.save()
                    messages.success(request, f'Reserva #{reserva.id} cancelada.')
                    
                elif accion == 'completar':
                    reserva.estado = 'COMPLETADA'
                    reserva.save()
                    
                    if reserva.ejemplar_asignado:
                        reserva.ejemplar_asignado.disponibilidad = 'PRESTADO'
                        reserva.ejemplar_asignado.save()
                        
                    messages.success(request, f'Reserva #{reserva.id} completada.')
                    
            except Reserva.DoesNotExist:
                messages.error(request, 'Reserva no encontrada')
            
            return redirect('gestionar_reservas')
        
        reservas = Reserva.objects.select_related(
            'socio__user', 'libro', 'ejemplar_asignado'
        ).order_by('-fecha_reserva')
        
        if search:
            reservas = reservas.filter(
                socio__user__first_name__icontains=search
            ) | reservas.filter(
                socio__user__last_name__icontains=search
            ) | reservas.filter(
                libro__titulo__icontains=search
            )
        
        context = {
            'reservas_pendientes': reservas.filter(estado='PENDIENTE'),
            'reservas_activas': reservas.filter(estado='ACTIVA'),
            'reservas_completadas': reservas.filter(estado='COMPLETADA')[:5],
            'reservas_canceladas': reservas.filter(estado='CANCELADA')[:5],
            'reservas_expiradas': reservas.filter(estado='EXPIRADA')[:5],
            'search': search,
            'hoy': timezone.now().date(),
        }
        
        return render(request, 'bibliotecario/reservas.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('dashboard_bibliotecario')


@staff_member_required
def gestionar_multas(request):
    """Gestionar usuarios morosos y multas pendientes"""
    from decimal import Decimal
    
    accion = request.GET.get('accion')
    multa_id = request.GET.get('multa_id')
    socio_id = request.GET.get('socio_id')
    search = request.GET.get('search', '')
    
    if accion == 'pagar' and multa_id:
        try:
            with transaction.atomic():
                multa = Multa.objects.select_related('prestamo__socio__user').get(id=multa_id, estado='PENDIENTE')
                
                multa.estado = 'PAGADA'
                multa.fecha_pago = timezone.now().date()
                
                if request.GET.get('comprobante'):
                    multa.comprobante_pago = request.GET.get('comprobante')
                
                multa.save()
                
                otras_multas = Multa.objects.filter(
                    prestamo__socio=multa.prestamo.socio,
                    estado='PENDIENTE'
                ).exclude(id=multa.id).count()
                
                if otras_multas == 0:
                    socio = multa.prestamo.socio
                    if socio.estado_socio == 'moroso':
                        socio.estado_socio = 'activo'
                        socio.save()
                
                messages.success(request, f'Multa #{multa.id} pagada correctamente. Monto: Gs. {multa.monto_total:,.0f}')
                
        except Multa.DoesNotExist:
            messages.error(request, 'Multa no encontrada')
        
        return redirect('gestionar_multas')
    
    multas_detalle = None
    socio_seleccionado = None
    total_multas_socio = 0
    
    if socio_id:
        try:
            socio_seleccionado = Socio.objects.get(id=socio_id)
            multas_detalle = Multa.objects.filter(
                prestamo__socio=socio_seleccionado,
                estado='PENDIENTE'
            ).select_related('prestamo__ejemplar__libro').order_by('fecha_generacion')
            total_multas_socio = multas_detalle.aggregate(total=Sum('monto_total'))['total'] or 0
        except Socio.DoesNotExist:
            pass
    
    socios_morosos = Socio.objects.filter(
        prestamos__multas__estado='PENDIENTE'
    ).distinct().select_related('user')
    
    if search:
        socios_morosos = socios_morosos.filter(
            user__first_name__icontains=search
        ) | socios_morosos.filter(
            user__last_name__icontains=search
        ) | socios_morosos.filter(
            cedula__icontains=search
        )
    
    socios_con_total = []
    for socio in socios_morosos:
        total_multas = Multa.objects.filter(
            prestamo__socio=socio,
            estado='PENDIENTE'
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        cantidad_multas = Multa.objects.filter(
            prestamo__socio=socio,
            estado='PENDIENTE'
        ).count()
        
        socios_con_total.append({
            'socio': socio,
            'total_multas': total_multas,
            'cantidad_multas': cantidad_multas
        })
    
    socios_con_total.sort(key=lambda x: x['total_multas'], reverse=True)
    
    context = {
        'socios_morosos': socios_con_total,
        'multas_detalle': multas_detalle,
        'socio_seleccionado': socio_seleccionado,
        'total_multas_socio': total_multas_socio,
        'search': search,
        'hoy': timezone.now().date(),
    }
    
    return render(request, 'bibliotecario/morosos.html', context)


@staff_member_required
def configuracion_panel(request):
    """Página de configuración del bibliotecario"""
    return render(request, 'bibliotecario/configuracion.html')


@staff_member_required
def mi_perfil(request):
    """Perfil del bibliotecario"""
    try:
        socio = Socio.objects.get(user=request.user)
    except Socio.DoesNotExist:
        socio = None
    
    context = {
        'user': request.user,
        'socio': socio,
    }
    return render(request, 'bibliotecario/perfil.html', context)


@staff_member_required
def buscar_usuario(request):
    """Buscar usuarios (socios) para el bibliotecario"""
    search = request.GET.get('search', '')
    socios = []
    socio_seleccionado = None
    prestamos_activos = []
    multas_pendientes = []
    
    if search:
        socios = Socio.objects.filter(estado_socio='activo').select_related('user')
        
        if search.isdigit():
            socios = socios.filter(cedula__icontains=search)
        else:
            socios = socios.filter(
                user__first_name__icontains=search
            ) | socios.filter(
                user__last_name__icontains=search
            )
        socios = socios[:10]
    
    socio_id = request.GET.get('socio_id')
    if socio_id:
        try:
            socio_seleccionado = Socio.objects.select_related('user').get(id=socio_id)
            prestamos_activos = Prestamo.objects.filter(
                socio=socio_seleccionado,
                estado='ACTIVO'
            ).select_related('ejemplar__libro').order_by('-fecha_prestamo')
            multas_pendientes = Multa.objects.filter(
                prestamo__socio=socio_seleccionado,
                estado='PENDIENTE'
            ).select_related('prestamo__ejemplar__libro')
        except Socio.DoesNotExist:
            pass
    
    context = {
        'socios': socios,
        'socio_seleccionado': socio_seleccionado,
        'prestamos_activos': prestamos_activos,
        'multas_pendientes': multas_pendientes,
        'search': search,
    }
    return render(request, 'bibliotecario/buscar_usuario.html', context)
@staff_member_required
def admin_dashboard(request):
    """Dashboard personalizado para el administrador"""
    
    hoy = timezone.now().date()
    
    # Estadísticas
    from django.contrib.auth.models import User
    from catalogo.models import Libro
    from prestamo.models import Prestamo, Multa
    
    total_usuarios = User.objects.count()
    total_libros = Libro.objects.count()
    prestamos_mes = Prestamo.objects.filter(
        fecha_prestamo__month=hoy.month,
        fecha_prestamo__year=hoy.year
    ).count()
    incidencias = Multa.objects.filter(estado='PENDIENTE').count()
    
    # Actividad reciente
    from usuario.models import Socio
    
    actividades = []
    
    # Últimos usuarios registrados
    ultimos_usuarios = User.objects.order_by('-date_joined')[:3]
    for u in ultimos_usuarios:
        try:
            tipo = u.socio.tipo_usuario if hasattr(u, 'socio') else 'Usuario'
        except:
            tipo = 'Usuario'
        actividades.append({
            'titulo': 'Nuevo usuario registrado',
            'descripcion': f'{u.get_full_name()} - Rol: {tipo}',
            'tiempo': u.date_joined
        })
    
    # Últimos libros agregados
    ultimos_libros = Libro.objects.order_by('-id')[:3]
    for l in ultimos_libros:
        actividades.append({
            'titulo': 'Libro agregado',
            'descripcion': f'"{l.titulo}" - Autor: {l.autores.first().nombre if l.autores.first() else "Desconocido"}',
            'tiempo': None  # No tenemos fecha de creación en Libro
        })
    
    # Últimos préstamos
    ultimos_prestamos = Prestamo.objects.select_related('socio__user', 'ejemplar__libro').order_by('-fecha_prestamo')[:2]
    for p in ultimos_prestamos:
        actividades.append({
            'titulo': 'Préstamo registrado',
            'descripcion': f'{p.socio.user.get_full_name()} - "{p.ejemplar.libro.titulo}"',
            'tiempo': p.fecha_prestamo
        })
    
    context = {
        'total_usuarios': total_usuarios,
        'total_libros': total_libros,
        'prestamos_mes': prestamos_mes,
        'incidencias': incidencias,
        'actividades': actividades[:6],
        'hoy': hoy,
    }
    return render(request, 'admin/dashboard.html', context)
