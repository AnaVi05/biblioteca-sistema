from django.core.management.base import BaseCommand
from catalogo.models import Libro

class Command(BaseCommand):
    help = 'Actualiza cantidad_total e inventario_disponible de todos los libros'

    def handle(self, *args, **options):
        libros = Libro.objects.all()
        for libro in libros:
            total = libro.ejemplares.count()
            disponibles = libro.ejemplares.filter(disponibilidad='DISPONIBLE').count()
            
            libro.cantidad_total = total
            libro.inventario_disponible = disponibles
            libro.save()
            
            self.stdout.write(f"{libro.titulo}: {disponibles}/{total} disponibles")
        
        self.stdout.write(self.style.SUCCESS("✅ ¡Inventario actualizado correctamente!"))