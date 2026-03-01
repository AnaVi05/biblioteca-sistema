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
