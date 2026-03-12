from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Prestamo

@staff_member_required
def lista_prestamos(request):
    """Lista todos los préstamos"""
    prestamos = Prestamo.objects.all().select_related('socio')
    
    # Filtros básicos
    estado = request.GET.get('estado')
    if estado:
        prestamos = prestamos.filter(estado=estado)
    
    context = {
        'prestamos': prestamos,
        'estados': Prestamo.ESTADO_PRESTAMO_CHOICES,
    }
    return render(request, 'prestamo/lista.html', context)

@staff_member_required
def detalle_prestamo(request, pk):
    """Detalle de un préstamo"""
    prestamo = get_object_or_404(Prestamo.objects.select_related('socio'), pk=pk)
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/detalle.html', context)

@staff_member_required
def crear_prestamo(request):
    """Vista para crear nuevo préstamo (placeholder)"""
    messages.warning(request, 'Funcionalidad en desarrollo - Esperando modelo Ejemplar')
    return redirect('lista_prestamos')

@staff_member_required
def devolver_prestamo(request, pk):
    """Registrar devolución de un préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if request.method == 'POST':
        prestamo.fecha_devolucion_real = timezone.now().date()
        prestamo.estado = 'DEVUELTO'
        prestamo.save()
        messages.success(request, f'Préstamo #{prestamo.id} marcado como devuelto')
        return redirect('detalle_prestamo', pk=prestamo.pk)
    
    context = {'prestamo': prestamo}
    return render(request, 'prestamo/devolver.html', context)