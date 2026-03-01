from django.contrib import admin
from .models import Autor,Editorial

@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'apellido')
    search_fields = ('nombre', 'apellido')

@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    
from django.contrib import admin
from .models import Autor, Editorial, Categoria  # Agregamos Categoria

# ... tus registros existentes de Autor y Editorial ...

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    list_display_links = ('id', 'nombre')