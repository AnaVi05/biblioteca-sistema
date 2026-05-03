from django.contrib import admin
from .models import Autor,Editorial,Ejemplar
from django.contrib import admin
from .models import Autor, Editorial, Categoria  
from .models import Autor, Editorial, Categoria, Libro, LibroAutor

@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'apellido')
    search_fields = ('nombre', 'apellido')

@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    list_display_links = ('id', 'nombre')


class LibroAutorInline(admin.TabularInline):
    model = LibroAutor
    extra = 1

@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ('id', 'isbn', 'titulo', 'editorial', 'categoria', 'cantidad_total', 'inventario_disponible')
    list_filter = ('editorial', 'categoria')
    search_fields = ('titulo', 'isbn')
    inlines = [LibroAutorInline]
   
@admin.register(Ejemplar)
class EjemplarAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo_inventario', 'libro', 'estado_fisico', 'disponibilidad', 'ubicacion')
    list_filter = ('estado_fisico', 'disponibilidad')
    search_fields = ('codigo_inventario', 'libro__titulo', 'ubicacion')
    autocomplete_fields = ['libro']
    list_editable = ('disponibilidad', 'ubicacion')