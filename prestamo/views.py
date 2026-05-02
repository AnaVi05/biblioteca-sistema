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
from django.http import JsonResponse
from decimal import Decimal
from .models import Prestamo, Multa, Reserva

@login_required
def api_notificaciones(request):
    """API para obtener notificaciones del usuario"""
    hoy = timezone.now().date()
    socio = request.user.socio
    
    notificaciones = []
    
    # Préstamos próximos a vencer
    prestamos_proximos = Prestamo.objects.filter(
        socio=socio,
        estado='ACTIVO',
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=3)
    )
    
    for p in prestamos_proximos:
        dias = (p.fecha_vencimiento - hoy).days
        notificaciones.append({
            'titulo': '📖 Préstamo próximo a vencer',
            'mensaje': f'"{p.ejemplar.libro.titulo}" vence en {dias} {"día" if dias == 1 else "días"}',
            'fecha': p.fecha_vencimiento.strftime("%d/%m/%Y"),
            'icono': 'fa-clock',
            'color': '#f59e0b',
            'leida': False
        })
    
    # Reservas listas para retirar
    reservas_listas = Reserva.objects.filter(
        socio=socio,
        estado='ACTIVA',
        fecha_expiracion__gte=hoy
    )
    
    for r in reservas_listas:
        notificaciones.append({
            'titulo': '✅ Reserva lista',
            'mensaje': f'"{r.libro.titulo}" está disponible para retirar',
            'fecha': r.fecha_expiracion.strftime("%d/%m/%Y"),
            'icono': 'fa-check-circle',
            'color': '#10b981',
            'leida': False
        })
    
    # Multas pendientes
    multas = Multa.objects.filter(prestamo__socio=socio, estado='PENDIENTE')
    total_multas = sum(m.monto_total for m in multas)
    if multas:
        notificaciones.append({
            'titulo': '💰 Multa pendiente',
            'mensaje': f'Tienes {multas.count()} {"multa" if multas.count() == 1 else "multas"} por un total de Gs. {total_multas:,.0f}',
            'fecha': hoy.strftime("%d/%m/%Y"),
            'icono': 'fa-exclamation-triangle',
            'color': '#dc2626',
            'leida': False
        })
    
    notificaciones.sort(key=lambda x: x['fecha'], reverse=True)
    return JsonResponse({'notificaciones': notificaciones})


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
    
    if ejemplar.disponibilidad != 'DISPONIBLE':
        messages.error(request, f'El ejemplar {ejemplar.codigo_inventario} no está disponible')
        return redirect('catalogo_lista')
    
    # ========== VALIDAR MULTAS PENDIENTES ==========
    multas_pendientes = Multa.objects.filter(
        prestamo__socio=request.user.socio,
        estado='PENDIENTE'
    )
    
    if multas_pendientes.exists():
        total_multa = sum(multa.monto_total for multa in multas_pendientes)
        messages.error(
            request, 
            f'❌ No puedes solicitar préstamos porque tienes {multas_pendientes.count()} multa(s) pendiente(s) por un total de Gs. {total_multa:,.0f}. '
            f'Debes pagar tu deuda para continuar.'
        )
        return redirect('catalogo_lista')
    
    # ========== VALIDAR PRÉSTAMOS VENCIDOS ==========
    hoy = date.today()
    prestamos_vencidos = Prestamo.objects.filter(
        socio=request.user.socio,
        estado='ACTIVO',
        fecha_vencimiento__lt=hoy
    )
    
    if prestamos_vencidos.exists():
        messages.error(
            request, 
            f'❌ No puedes solicitar préstamos porque tienes {prestamos_vencidos.count()} préstamo(s) vencido(s) sin devolver. '
            f'Debes devolver los libros atrasados para continuar.'
        )
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
    
    # ========== MULTAS PENDIENTES ==========
    multas_pendientes = Multa.objects.filter(
        prestamo__socio=request.user.socio,
        estado='PENDIENTE'
    ).select_related('prestamo__ejemplar__libro')
    
    context = {
        'activos': prestamos_activos,
        'solicitados': prestamos_solicitados,
        'historial': historial,
        'multas_pendientes': multas_pendientes,  # ← Agrega esta línea
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
    """Permite al usuario reservar un libro"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    # ========== VALIDAR MULTAS PENDIENTES ==========
    multas_pendientes = Multa.objects.filter(
        prestamo__socio=request.user.socio,
        estado='PENDIENTE'
    )
    
    if multas_pendientes.exists():
        total_multa = sum(multa.monto_total for multa in multas_pendientes)
        messages.error(
            request, 
            f'❌ No puedes reservar libros porque tienes {multas_pendientes.count()} multa(s) pendiente(s) por un total de Gs. {total_multa:,.0f}. '
            f'Debes pagar tu deuda para continuar.'
        )
        return redirect('catalogo_lista')
    
    # ========== VALIDAR PRÉSTAMOS VENCIDOS ==========
    hoy = date.today()
    prestamos_vencidos = Prestamo.objects.filter(
        socio=request.user.socio,
        estado='ACTIVO',
        fecha_vencimiento__lt=hoy
    )
    
    if prestamos_vencidos.exists():
        messages.error(
            request, 
            f'❌ No puedes reservar libros porque tienes {prestamos_vencidos.count()} préstamo(s) vencido(s) sin devolver. '
            f'Debes devolver los libros atrasados para continuar.'
        )
        return redirect('catalogo_lista')
    
    # ========== VALIDAR LÍMITE DE RESERVAS ACTIVAS ==========
    reservas_activas_total = Reserva.objects.filter(
        socio=request.user.socio,
        estado__in=['PENDIENTE', 'ACTIVA']
    ).count()
    
    if reservas_activas_total >= 3:
        messages.warning(
            request, 
            f'⚠️ Tienes {reservas_activas_total} reservas activas. El límite máximo es 3 reservas simultáneas.'
        )
        return redirect('mis_reservas')
    
    # Contar ejemplares disponibles
    ejemplares_disponibles = Ejemplar.objects.filter(
        libro=libro, 
        disponibilidad='DISPONIBLE'
    ).count()
    
    # Si hay 2 o más ejemplares, redirigir a préstamo (no a reserva)
    if ejemplares_disponibles >= 2:
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
        
        # ========== VALIDAR QUE NO TENGA RESERVA ACTIVA PARA ESTE MISMO LIBRO ==========
        reserva_activa = Reserva.objects.filter(
            socio=request.user.socio,
            libro=libro,
            estado__in=['PENDIENTE', 'ACTIVA']
        ).exists()
        
        if reserva_activa:
            messages.warning(
                request, 
                f'⚠️ Ya tienes una reserva activa o pendiente para el libro "{libro.titulo}". '
                f'Debes cancelarla o esperar a que expire para hacer una nueva reserva.'
            )
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
        
        # Mensaje según la situación
        if ejemplares_disponibles == 1:
            messages.success(
                request, 
                f'✅ ¡Libro reservado! El único ejemplar disponible es para consulta en sala. '
                f'Te avisaremos cuando se libere otro ejemplar para préstamo. Estás en la posición {reserva.orden_prioridad} de la cola.'
            )
        else:
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
    from datetime import date
    hoy = date.today()
    
    # Marcar reservas expiradas y mostrar notificación
    reservas_expiradas = Reserva.objects.filter(
        socio=request.user.socio,
        estado='PENDIENTE',
        fecha_expiracion__lt=hoy
    )
    
    for reserva in reservas_expiradas:
        reserva.estado = 'EXPIRADA'
        reserva.save()
        messages.warning(request, f'⚠️ Tu reserva de "{reserva.libro.titulo}" ha expirado porque no la retiraste a tiempo.')
    
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
        'hoy': hoy,
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
    
    # ========== ESTADÍSTICAS PRINCIPALES ==========
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
    
    # Solicitudes pendientes
    solicitudes_pendientes = Prestamo.objects.filter(
        estado='SOLICITADO'
    ).select_related('socio__user', 'ejemplar__libro').order_by('fecha_prestamo')
    
    # ========== TAREAS PENDIENTES ==========
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
    
    # ========== ACTIVIDAD RECIENTE ==========
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
    
    # ========== NOTIFICACIONES DE COMPROBANTES ==========
    comprobantes_pendientes = Multa.objects.filter(
        comprobante_imagen__isnull=False,
        notificado=False,
        estado='PENDIENTE'
    ).select_related('prestamo__socio__user', 'prestamo__ejemplar__libro')
    
    notificaciones_comprobantes = []
    for multa in comprobantes_pendientes:
        notificaciones_comprobantes.append({
            'id': multa.id,
            'mensaje': f'El usuario {multa.prestamo.socio.user.get_full_name()} ha subido un comprobante de pago',
            'monto': multa.monto_total,
            'libro': multa.prestamo.ejemplar.libro.titulo,
            'fecha': multa.fecha_generacion,
        })
    
    # Marcar como notificadas
    for multa in comprobantes_pendientes:
        multa.notificado = True
        multa.save()
    
    context = {
        # Estadísticas principales
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
        
        # Solicitudes
        'solicitudes_pendientes': solicitudes_pendientes,
        
        # Tareas y actividades
        'tareas_pendientes': tareas_pendientes,
        'actividades_recientes': actividades_recientes,
        
        # Notificaciones de comprobantes
        'notificaciones_comprobantes': notificaciones_comprobantes,
        'total_notificaciones': len(notificaciones_comprobantes),
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
            
            # Actualizar inventario del libro
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
                    
                    # ========== VALIDAR MULTAS PENDIENTES ==========
                    tiene_multas = Multa.objects.filter(
                        prestamo__socio=socio,
                        estado='PENDIENTE'
                    ).exists()
                    
                    if tiene_multas:
                        messages.warning(request, '⚠️ El socio tiene multas pendientes')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
                    # ========== VALIDAR PRÉSTAMOS VENCIDOS ==========
                    hoy = date.today()
                    prestamos_vencidos = Prestamo.objects.filter(
                        socio=socio,
                        estado='ACTIVO',
                        fecha_vencimiento__lt=hoy
                    ).exists()
                    
                    if prestamos_vencidos:
                        messages.warning(request, '⚠️ El socio tiene préstamos vencidos sin devolver')
                        return redirect('prestamo_nuevo_bibliotecario')
                    
                    # Crear préstamo
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
                    
                    messages.success(request, f'✅ Préstamo #{prestamo.id} registrado exitosamente')
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
    
    # Obtener préstamos activos
    prestamos_activos = Prestamo.objects.filter(
        estado='ACTIVO'
    ).select_related(
        'socio__user', 'ejemplar__libro'
    ).order_by('fecha_vencimiento')
    
    # Búsqueda
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
    
    # Si se selecciona un préstamo para devolver
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
    
    # Procesar devolución
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
                
                # Calcular atraso
                if prestamo.fecha_vencimiento < hoy:
                    dias_atraso = (hoy - prestamo.fecha_vencimiento).days
                    monto_por_dia = Decimal('1000')
                    monto_multa = dias_atraso * monto_por_dia
                
                # Registrar fecha de devolución
                prestamo.fecha_devolucion_real = hoy
                prestamo.estado = 'DEVUELTO'
                prestamo.save()
                
                # Actualizar disponibilidad del ejemplar
                prestamo.ejemplar.disponibilidad = 'DISPONIBLE'
                prestamo.ejemplar.save()
                
                # ========== ACTUALIZAR INVENTARIO DEL LIBRO ==========
                libro = prestamo.ejemplar.libro
                libro.inventario_disponible = Ejemplar.objects.filter(
                    libro=libro, 
                    disponibilidad='DISPONIBLE'
                ).count()
                libro.save()
                
                # Crear multa si hay atraso
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
                    messages.warning(request, f'⚠️ Devolución registrada. Multa generada: Gs. {monto_multa:,.0f} por {dias_atraso} días de atraso.')
                else:
                    messages.success(request, f'✅ Devolución registrada exitosamente. Préstamo #{prestamo.id} completado.')
                
                return redirect('registrar_devolucion')
                
        except Prestamo.DoesNotExist:
            messages.error(request, '❌ Préstamo no encontrado')
        except Exception as e:
            messages.error(request, f'❌ Error al procesar devolución: {str(e)}')
    
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
        # ========== ELIMINAR RESERVAS EXPIRADAS ==========
        ahora = timezone.now()
        reservas_expiradas = Reserva.objects.filter(
            estado='PENDIENTE',
            fecha_expiracion__lt=ahora
        )
        
        expiradas_count = reservas_expiradas.count()
        for reserva in reservas_expiradas:
            reserva.estado = 'EXPIRADA'
            reserva.save()
            # Si tenía un ejemplar asignado, liberarlo
            if reserva.ejemplar_asignado:
                reserva.ejemplar_asignado.disponibilidad = 'DISPONIBLE'
                reserva.ejemplar_asignado.save()
        
        if expiradas_count > 0:
            messages.info(request, f'ℹ️ {expiradas_count} reserva(s) expirada(s) han sido canceladas automáticamente.')
        
        # ========== PROCESAR ACCIONES ==========
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
                            
                            messages.success(request, f'✅ Reserva #{reserva.id} confirmada. Ejemplar {ejemplar_disponible.codigo_inventario} reservado.')
                        else:
                            messages.warning(request, f'⚠️ No hay ejemplares disponibles para "{reserva.libro.titulo}"')
                            
                elif accion == 'cancelar':
                    with transaction.atomic():
                        if reserva.ejemplar_asignado:
                            reserva.ejemplar_asignado.disponibilidad = 'DISPONIBLE'
                            reserva.ejemplar_asignado.save()
                        
                        reserva.estado = 'CANCELADA'
                        reserva.save()
                        messages.success(request, f'✅ Reserva #{reserva.id} cancelada correctamente.')
                        
                elif accion == 'completar':
                    with transaction.atomic():
                        if not reserva.ejemplar_asignado:
                            messages.error(request, '❌ Esta reserva no tiene un ejemplar asignado.')
                            return redirect('gestionar_reservas')
                        
                        reserva.estado = 'COMPLETADA'
                        reserva.save()
                        
                        ejemplar = reserva.ejemplar_asignado
                        ejemplar.disponibilidad = 'PRESTADO'
                        ejemplar.save()
                        
                        # Obtener días de préstamo desde configuración
                        try:
                            from prestamo.models import Configuracion
                            dias_prestamo = Configuracion.get_config().dias_maximos_prestamo
                        except:
                            dias_prestamo = 5
                        
                        fecha_prestamo = timezone.now()
                        fecha_vencimiento = fecha_prestamo.date() + timedelta(days=dias_prestamo)
                        
                        prestamo = Prestamo.objects.create(
                            socio=reserva.socio,
                            ejemplar=ejemplar,
                            dias_solicitados=dias_prestamo,
                            fecha_prestamo=fecha_prestamo,
                            fecha_vencimiento=fecha_vencimiento,
                            estado='ACTIVO'
                        )
                        
                        messages.success(request, f'✅ Reserva #{reserva.id} completada. Préstamo #{prestamo.id} creado.')
                        
            except Reserva.DoesNotExist:
                messages.error(request, '❌ Reserva no encontrada')
            
            return redirect('gestionar_reservas')
        
        # ========== OBTENER RESERVAS ==========
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
        messages.error(request, f'❌ Error: {str(e)}')
        return redirect('dashboard_bibliotecario')
@staff_member_required
def gestionar_multas(request):
    """Gestionar usuarios morosos y multas pendientes"""
    from decimal import Decimal
    
    accion = request.GET.get('accion')
    multa_id = request.GET.get('multa_id')
    socio_id = request.GET.get('socio_id')
    search = request.GET.get('search', '')
    
    # Procesar pago de multa (confirmar pago por bibliotecario)
    if accion == 'pagar' and multa_id:
        try:
            with transaction.atomic():
                multa = Multa.objects.select_related('prestamo__socio__user').get(id=multa_id, estado='PENDIENTE')
                
                multa.estado = 'PAGADA'
                multa.fecha_pago = timezone.now().date()
                
                if request.GET.get('comprobante'):
                    multa.comprobante_pago = request.GET.get('comprobante')
                
                multa.save()
                
                # Verificar si el socio ya no tiene más multas pendientes
                otras_multas = Multa.objects.filter(
                    prestamo__socio=multa.prestamo.socio,
                    estado='PENDIENTE'
                ).exclude(id=multa.id).count()
                
                if otras_multas == 0:
                    socio = multa.prestamo.socio
                    if socio.estado_socio == 'moroso':
                        socio.estado_socio = 'activo'
                        socio.save()
                
                messages.success(request, f'✅ Multa #{multa.id} pagada correctamente. Monto: Gs. {multa.monto_total:,.0f}')
                
        except Multa.DoesNotExist:
            messages.error(request, '❌ Multa no encontrada')
        
        return redirect('gestionar_multas')
    
    # Ver detalle de multas de un socio específico
    multas_detalle = None
    socio_seleccionado = None
    total_multas_socio = 0
    
    if socio_id:
        try:
            socio_seleccionado = Socio.objects.get(id=socio_id)
            multas_detalle = Multa.objects.filter(
                prestamo__socio=socio_seleccionado,
                estado='PENDIENTE'
            ).select_related('prestamo__ejemplar__libro', 'prestamo__socio__user').order_by('fecha_generacion')
            total_multas_socio = multas_detalle.aggregate(total=Sum('monto_total'))['total'] or 0
        except Socio.DoesNotExist:
            pass
    
    # Obtener todos los socios con multas pendientes
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
    
    # Calcular total de multas por socio
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

# ========== REPORTES ==========
@staff_member_required
def reporte_reservas_expiradas(request):
    """Reporte de reservas expiradas"""
    reservas = Reserva.objects.filter(estado='EXPIRADA').select_related('socio__user', 'libro')
    context = {'reservas': reservas}
    return render(request, 'bibliotecario/reporte_reservas_expiradas.html', context)

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


#reportes de usuarios activos 
from usuario.models import Socio
from django.db.models import Count, Q

@staff_member_required
def reporte_usuarios_activos(request):
    """Reporte de usuarios activos (estado_socio = 'activo')"""
    
    # Obtener todos los socios activos
    socios = Socio.objects.filter(estado_socio='activo').select_related('user')
    
    # Agregar información adicional (cantidad de préstamos activos, multas, etc.)
    for socio in socios:
        socio.prestamos_activos = Prestamo.objects.filter(
            socio=socio, 
            estado='ACTIVO'
        ).count()
        socio.multas_pendientes = Multa.objects.filter(
            prestamo__socio=socio,
            estado='PENDIENTE'
        ).count()
        socio.total_multas = sum(m.monto_total for m in Multa.objects.filter(
            prestamo__socio=socio, estado='PENDIENTE'
        ))
    
    # Filtros opcionales (por tipo de usuario, por búsqueda)
    tipo_usuario = request.GET.get('tipo_usuario', '')
    search = request.GET.get('search', '')
    
    if tipo_usuario:
        socios = socios.filter(tipo_usuario=tipo_usuario)
    
    if search:
        socios = socios.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(cedula__icontains=search)
        )
    
    context = {
        'socios': socios,
        'tipo_usuario': tipo_usuario,
        'search': search,
        'total_activos': socios.count(),
        'tipos_usuario': Socio.TIPO_USUARIO_CHOICES,
    }
    return render(request, 'bibliotecario/reporte_usuarios_activos.html', context)

@staff_member_required
def reporte_usuarios_morosos(request):
    """Reporte de usuarios morosos con detalle de atrasos"""
    from datetime import date
    from django.db.models import Q
    from decimal import Decimal
    
    hoy = date.today()
    
    # Usuarios con multas pendientes
    socios_con_multas = Socio.objects.filter(
        prestamos__multas__estado='PENDIENTE'
    ).distinct().select_related('user')
    
    # También usuarios con préstamos vencidos (aunque no tengan multa aún)
    socios_vencidos = Socio.objects.filter(
        prestamos__estado='ACTIVO',
        prestamos__fecha_vencimiento__lt=hoy
    ).distinct().select_related('user')
    
    # Combinar ambos
    socios_morosos = list(socios_con_multas) + list(socios_vencidos)
    socios_morosos = list({s.id: s for s in socios_morosos}.values())  # Eliminar duplicados
    
    for socio in socios_morosos:
        # Multas pendientes del socio
        multas = Multa.objects.filter(
            prestamo__socio=socio,
            estado='PENDIENTE'
        ).select_related('prestamo__ejemplar__libro')
        
        socio.detalle_multas = multas
        socio.total_multas = sum(m.monto_total for m in multas)
        socio.cantidad_multas = multas.count()
        
        # Préstamos vencidos (ACTIVOS con fecha vencimiento pasada)
        prestamos_vencidos = Prestamo.objects.filter(
            socio=socio,
            estado='ACTIVO',
            fecha_vencimiento__lt=hoy
        )
        
        socio.prestamos_vencidos = prestamos_vencidos
        socio.total_dias_atraso = sum(
            (hoy - p.fecha_vencimiento).days for p in prestamos_vencidos
        )
    
    # Filtro por búsqueda
    search = request.GET.get('search', '')
    if search:
        socios_morosos = [
            s for s in socios_morosos if 
            search.lower() in s.user.get_full_name().lower() or
            search in s.cedula
        ]
    
    context = {
        'socios_morosos': socios_morosos,
        'search': search,
        'total_morosos': len(socios_morosos),
        'hoy': hoy,
        'ahora': timezone.now(),
    }
    return render(request, 'bibliotecario/reporte_usuarios_morosos.html', context)

@staff_member_required
def reporte_usuarios_inhabilitados(request):
    """Reporte de usuarios inhabilitados (estado_socio = 'inhabilitado')"""
    from django.db.models import Q
    
    # Usuarios con estado inhabilitado
    socios = Socio.objects.filter(estado_socio='inhabilitado').select_related('user')
    
    for socio in socios:
        # Motivo de inhabilitación (si lo tienes en algún campo)
        socio.motivo = socio.observaciones if hasattr(socio, 'observaciones') else "No especificado"
        socio.fecha_inhabilitacion = socio.fecha_registro  # o un campo específico
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        socios = socios.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(cedula__icontains=search)
        )
    
    context = {
        'socios': socios,
        'search': search,
        'total_inhabilitados': socios.count(),
        'hoy': date.today(),
        'ahora': timezone.now(),
    }
    return render(request, 'bibliotecario/reporte_usuarios_inhabilitados.html', context)

@staff_member_required
def reporte_prestamos_vencidos(request):
    """Reporte de préstamos vencidos que no han sido devueltos"""
    from datetime import date
    from django.db.models import Q
    
    hoy = date.today()
    
    # Préstamos ACTIVOS con fecha de vencimiento anterior a hoy
    prestamos = Prestamo.objects.filter(
        estado='ACTIVO',
        fecha_vencimiento__lt=hoy
    ).select_related('socio__user', 'ejemplar__libro')
    
    
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        prestamos = prestamos.filter(
            Q(socio__user__first_name__icontains=search) |
            Q(socio__user__last_name__icontains=search) |
            Q(ejemplar__libro__titulo__icontains=search)
        )
    
    context = {
        'prestamos': prestamos,
        'search': search,
        'total_vencidos': prestamos.count(),
        'hoy': hoy,
        'ahora': timezone.now(),
    }
    return render(request, 'bibliotecario/reporte_prestamos_vencidos.html', context)

from django.db.models import Count

@staff_member_required
def reporte_libros_demanda(request):
    """Reporte de libros más y menos prestados para análisis de demanda"""
    from datetime import date, timedelta
    
    # Período de análisis (últimos 30 días por defecto)
    periodos = {
        '30': 'Últimos 30 días',
        '90': 'Últimos 90 días',
        '365': 'Último año',
        'todo': 'Todo el historial'
    }
    
    periodo = request.GET.get('periodo', '30')
    hoy = date.today()
    
    # Filtrar por fecha según período
    fecha_inicio = None
    if periodo != 'todo':
        dias = int(periodo)
        fecha_inicio = hoy - timedelta(days=dias)
    
    # Base de datos de préstamos
    prestamos_query = Prestamo.objects.all()
    if fecha_inicio:
        prestamos_query = prestamos_query.filter(fecha_prestamo__date__gte=fecha_inicio)
    
    # Libros más prestados (top 10)
    libros_mas_prestados = Libro.objects.annotate(
        total_prestamos=Count('ejemplares__prestamos', distinct=True)
    ).filter(total_prestamos__gt=0).order_by('-total_prestamos')[:10]
    
    # Libros menos prestados (bottom 10, que tengan al menos 1 ejemplar)
    libros_menos_prestados = Libro.objects.annotate(
        total_prestamos=Count('ejemplares__prestamos', distinct=True)
    ).filter(ejemplares__isnull=False).distinct().order_by('total_prestamos')[:10]
    
    # Calcular total de préstamos en el período
    total_prestamos_periodo = prestamos_query.count()
    
    context = {
        'libros_mas_prestados': libros_mas_prestados,
        'libros_menos_prestados': libros_menos_prestados,
        'periodos': periodos,
        'periodo_actual': periodo,
        'total_prestamos': total_prestamos_periodo,
        'fecha_inicio': fecha_inicio,
        'hoy': hoy,
        'ahora': timezone.now(),
    }
    return render(request, 'bibliotecario/reporte_libros_demanda.html', context)

@login_required
def subir_comprobante(request, multa_id):
    """Usuario sube comprobante de pago para una multa"""
    multa = get_object_or_404(
        Multa, 
        id=multa_id, 
        prestamo__socio=request.user.socio,
        estado='PENDIENTE'
    )
    
    if request.method == 'POST':
        if request.FILES.get('comprobante'):
            multa.comprobante_imagen = request.FILES['comprobante']
            multa.notificado = False  # Nueva notificación pendiente
            multa.save()
            messages.success(request, '✅ Comprobante subido correctamente. El bibliotecario será notificado.')
        else:
            messages.error(request, '❌ Debes seleccionar una imagen')
    
    return redirect('mis_prestamos')
