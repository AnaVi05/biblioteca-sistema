from django.db import models

class Autor(models.Model):
    """Autores de los libros"""
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores"
    
    def __str__(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
class Editorial(models.Model):
    """Editoriales de los libros"""
    nombre = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Nombre de la editorial"
    )
    
    class Meta:
        verbose_name = "Editorial"
        verbose_name_plural = "Editoriales"
    
    def __str__(self):
        return self.nombre
class Categoria(models.Model):
    """Categorías para clasificar los libros"""
    nombre = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Nombre de la categoría"
    )
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']  # Orden alfabético
    
    def __str__(self):
        return self.nombre
    


class Libro(models.Model):
    """Libros del catálogo"""
    isbn = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="ISBN"
    )
    titulo = models.CharField(
        max_length=200, 
        verbose_name="Título"
    )
    anio_publicacion = models.IntegerField(
        blank=True, 
        null=True, 
        verbose_name="Año de publicación"
    )
    descripcion = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Descripción / Sinopsis",
        help_text="Breve descripción o sinopsis del libro"
    )
    editorial = models.ForeignKey(
        Editorial, 
        on_delete=models.PROTECT, 
        verbose_name="Editorial"
    )
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.PROTECT, 
        verbose_name="Categoría"
    )
    autores = models.ManyToManyField(
        Autor, 
        through='LibroAutor', 
        verbose_name="Autores"
    )

    imagen = models.ImageField(
        upload_to='libros/', 
        blank=True, 
        null=True,
        verbose_name="Imagen de tapa"
    )
    cantidad_total = models.IntegerField(
        default=0, 
        verbose_name="Total de ejemplares"
    )
    inventario_disponible = models.IntegerField(
        default=0, 
        verbose_name="Ejemplares disponibles"
    )
    
    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"
    
    def __str__(self):
        return f"{self.titulo} ({self.isbn})"
    

class LibroAutor(models.Model):
    """Relación entre libros y autores"""
    ROL_CHOICES = [
        ('principal', 'Autor Principal'),
        ('coautor', 'Coautor'),
        ('colaborador', 'Colaborador'),
    ]
    
    libro = models.ForeignKey(
        Libro, 
        on_delete=models.CASCADE,
        verbose_name="Libro"
    )
    autor = models.ForeignKey(
        Autor, 
        on_delete=models.CASCADE,
        verbose_name="Autor"
    )
    rol_autor = models.CharField(
        max_length=50, 
        choices=ROL_CHOICES, 
        blank=True, 
        null=True,
        verbose_name="Rol del autor"
    )
    observacion = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name="Observaciones"
    )
    
    class Meta:
        verbose_name = "Relación Libro-Autor"
        verbose_name_plural = "Relaciones Libro-Autores"
        unique_together = ['libro', 'autor']  
    
    def __str__(self):
        return f"{self.libro.titulo} - {self.autor.nombre_completo}"