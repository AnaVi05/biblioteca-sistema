from django.db import models
from usuario.models import Socio
from catalogo.models import Ejemplar  # COMENTADO hasta que feature/ejemplar se fusione

class Prestamo(models.Model):
    """Préstamos de ejemplares a socios"""
    
    ESTADO_PRESTAMO_CHOICES = [
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
    
    # ⚠️ COMENTADO hasta que feature/ejemplar se fusione a main
    ejemplar = models.ForeignKey(
        Ejemplar, 
         on_delete=models.PROTECT,
        related_name='prestamos',
        verbose_name="Ejemplar"
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
    
    @property
    def dias_atraso(self):
        """Calcula días de atraso si corresponde"""
        from django.utils import timezone
        
        # Si no hay fecha de vencimiento, no hay atraso
        if not self.fecha_vencimiento:
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
    
    def marcar_extraviado(self):
        """Marca el préstamo como extraviado"""
        self.estado = 'EXTRAVIADO'
        self.save()

class Multa(models.Model):
    """Multas por devoluciones tardías"""
    
    ESTADO_MULTA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    prestamo = models.ForeignKey(
        'Prestamo',
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