from django.db import models
from django.contrib.auth.models import User

class NivelAcceso(models.Model):
    """Niveles de acceso del sistema"""
    nombre = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Nivel de Acceso"
        verbose_name_plural = "Niveles de Acceso"
    
    def __str__(self):
        return self.nombre

class Socio(models.Model):
    """Perfil extendido del usuario de Django"""
    
    TIPO_USUARIO_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('administrativo', 'Administrativo'),
        ('externo', 'Externo'),
    ]
    
    ESTADO_SOCIO_CHOICES = [
        ('activo', 'Activo'),
        ('moroso', 'Moroso'),
        ('inhabilitado', 'Inhabilitado'),
    ]
    
    # Relación 1 a 1 con el usuario de Django
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name="Usuario de Django"
    )
    
    # Campos adicionales específicos de la biblioteca
    cedula = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Cédula"
    )
    
    telefono = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Teléfono"
    )
    
    direccion = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        verbose_name="Dirección"
    )
    
    carrera = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Carrera/Profesión"
    )
    
    tipo_usuario = models.CharField(
        max_length=50, 
        choices=TIPO_USUARIO_CHOICES,
        verbose_name="Tipo de usuario"
    )
    
    estado_socio = models.CharField(
        max_length=20, 
        choices=ESTADO_SOCIO_CHOICES,
        default='activo',
        verbose_name="Estado"
    )
    
    fecha_registro = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de registro"
    )
    
    nivel_acceso = models.ForeignKey(
        NivelAcceso, 
        on_delete=models.PROTECT,
        verbose_name="Nivel de acceso"
    )
    
    class Meta:
        verbose_name = "Socio"
        verbose_name_plural = "Socios"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.cedula}"
    
    @property
    def nombre_completo(self):
        return self.user.get_full_name()