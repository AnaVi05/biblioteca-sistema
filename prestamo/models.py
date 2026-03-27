from django.db import models
from usuario.models import Socio
from catalogo.models import Ejemplar
from django.utils import timezone
from datetime import timedelta

class Prestamo(models.Model):
    """Préstamos de ejemplares a socios"""
    
    ESTADO_PRESTAMO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('ACTIVO', 'Activo'),
        ('VENCIDO', 'Vencido'),
        ('DEVUELTO', 'Devuelto'),
        ('EXTRAVIADO', 'Extraviado'),
    ]
    
    socio = models.ForeignKey(
        Socio, 
        on_delete=models.PROTECT,
        related_name='prestamos',
        verbose_name="Socio"
    )
    
    ejemplar = models.ForeignKey(
        Ejemplar, 
        on_delete=models.PROTECT,
        related_name='prestamos',
        verbose_name="Ejemplar"
    )
    
    
    dias_solicitados = models.IntegerField(
        verbose_name="Días solicitados",
        help_text="Cantidad de días que el usuario pidió el libro (1-5)",
        null=True,  
        blank=True
    )
    
    fecha_prestamo = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de préstamo"
    )
    fecha_vencimiento = models.DateField(
        verbose_name="Fecha de vencimiento"
    )
    fecha_devolucion_real = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha de devolución real"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_PRESTAMO_CHOICES,
        default='ACTIVO',
        verbose_name="Estado"
    )
    observaciones = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Observaciones"
    )
    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_prestamo']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]
    
    def __str__(self):
        return f"Préstamo #{self.id} - {self.socio}"
    
    def save(self, *args, **kwargs):
        # Si no hay fecha_vencimiento pero hay dias_solicitados, calcularla
        if not self.fecha_vencimiento and self.dias_solicitados:
            from datetime import timedelta
            self.fecha_vencimiento = self.fecha_prestamo.date() + timedelta(days=self.dias_solicitados)
        super().save(*args, **kwargs)
    
    @property
    def dias_atraso(self):
        """Calcula días de atraso si corresponde"""
        from django.utils import timezone
        
        # Si no hay fecha de vencimiento, no hay atraso
        if not self.fecha_vencimiento:
            return 0
        
        # Si está extraviado, no calculamos atraso normal
        if self.estado == 'EXTRAVIADO':
            return 0
        
        # Caso 1: Ya fue devuelto
        if self.fecha_devolucion_real:
            if self.fecha_devolucion_real > self.fecha_vencimiento:
                return (self.fecha_devolucion_real - self.fecha_vencimiento).days
            return 0
        
        # Caso 2: Aún no devuelto
        hoy = timezone.now().date()
        if hoy > self.fecha_vencimiento:
            return (hoy - self.fecha_vencimiento).days
        
        return 0
    
    @property
    def esta_vencido(self):
        """Indica si el préstamo está vencido"""
        from django.utils import timezone
        if not self.fecha_devolucion_real and self.fecha_vencimiento:
            return self.fecha_vencimiento < timezone.now().date()
        return False
    
    def marcar_devuelto(self):
        """Marca el préstamo como devuelto"""
        from django.utils import timezone
        self.fecha_devolucion_real = timezone.now().date()
        self.estado = 'DEVUELTO'
        self.save()
        
        # Actualizar disponibilidad del ejemplar
        if self.ejemplar:
            self.ejemplar.disponibilidad = 'disponible'
            self.ejemplar.save()
    
    def marcar_extraviado(self, observaciones=""):
        """Marca el préstamo como extraviado y genera multa especial"""
        self.estado = 'EXTRAVIADO'
        self.observaciones = observaciones
        self.save()
        
        # Marcar el ejemplar como extraviado
        if self.ejemplar:
            self.ejemplar.estado_fisico = 'extraviado'
            self.ejemplar.disponibilidad = 'no_disponible'
            self.ejemplar.save()
        
        # Generar multa por extravío (valor del libro + penalización)
        # Buscar o crear multa asociada
        multa, created = Multa.objects.get_or_create(
            prestamo=self,
            defaults={
                'dias_atraso': 0,
                'monto_base': 50000,  # Valor base del libro
                'monto_por_dia': 0,
                'monto_total': 50000,  # Podría ser el precio del libro
                'estado': 'PENDIENTE'
            }
        )
        return multa


class Reserva(models.Model):
    """Reservas de libros por socios"""
    
    ESTADO_RESERVA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ACTIVA', 'Activa'),
        ('CANCELADA', 'Cancelada'),
        ('COMPLETADA', 'Completada'),
        ('EXPIRADA', 'Expirada'),
    ]
    
    socio = models.ForeignKey(
        Socio,
        on_delete=models.PROTECT,
        related_name='reservas',
        verbose_name="Socio"
    )
    libro = models.ForeignKey(
        'catalogo.Libro',
        on_delete=models.PROTECT,
        related_name='reservas',
        verbose_name="Libro"
    )
    fecha_reserva = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de reserva"
    )
    fecha_expiracion = models.DateTimeField(
        verbose_name="Fecha de expiración"
    )
    orden_prioridad = models.IntegerField(
        default=1,
        verbose_name="Orden de prioridad"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_RESERVA_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    ejemplar_asignado = models.ForeignKey(
        Ejemplar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
        verbose_name="Ejemplar asignado"
    )
    
    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['estado', 'orden_prioridad', 'fecha_reserva']
        unique_together = ['socio', 'libro', 'estado']  
    
    def __str__(self):
        return f"Reserva {self.id} - {self.socio} - {self.libro.titulo}"
    
    def activar(self, ejemplar):
        """Activa la reserva asignando un ejemplar"""
        self.estado = 'ACTIVA'
        self.ejemplar_asignado = ejemplar
        self.save()
        
        
    
    def cancelar(self):
        """Cancela la reserva"""
        self.estado = 'CANCELADA'
        self.save()
    
    def expirar(self):
        """Marca la reserva como expirada"""
        self.estado = 'EXPIRADA'
        self.save()
    
    def completar(self):
        """Marca la reserva como completada (el usuario retiró el libro)"""
        self.estado = 'COMPLETADA'
        self.save()


class Multa(models.Model):
    """Multas por devoluciones tardías o extravío"""
    
    ESTADO_MULTA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.PROTECT,
        related_name='multas',
        verbose_name="Préstamo"
    )
    dias_atraso = models.IntegerField(
        verbose_name="Días de atraso"
    )
    monto_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto base"
    )
    monto_por_dia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto por día"
    )
    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto total"
    )
    fecha_generacion = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de generación"
    )
    fecha_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_MULTA_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    comprobante_pago = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Comprobante de pago"
    )
    
    class Meta:
        verbose_name = "Multa"
        verbose_name_plural = "Multas"
    
    def __str__(self):
        return f"Multa #{self.id} - Préstamo #{self.prestamo_id} - Gs. {self.monto_total}"
    
    def save(self, *args, **kwargs):
        # Calcular monto total si no está definido
        if not self.monto_total and self.dias_atraso > 0:
            self.monto_total = self.monto_base + (self.dias_atraso * self.monto_por_dia)
        super().save(*args, **kwargs)
    
    def pagar(self, comprobante=""):
        """Registra el pago de la multa"""
        from django.utils import timezone
        self.fecha_pago = timezone.now().date()
        self.estado = 'PAGADA'
        if comprobante:
            self.comprobante_pago = comprobante
        self.save()

