from django.db import models
from usuario.models import Socio
# from catalogo.models import Ejemplar  # COMENTADO hasta que feature/ejemplar se fusione

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
    # ejemplar = models.ForeignKey(
    #     Ejemplar, 
    #     on_delete=models.PROTECT,
    #     related_name='prestamos',
    #     verbose_name="Ejemplar"
    # )
    
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