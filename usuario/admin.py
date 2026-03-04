from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import NivelAcceso, Socio

class SocioInline(admin.StackedInline):
    """Para mostrar Socio dentro del admin de User"""
    model = Socio
    can_delete = False
    verbose_name_plural = 'Datos de Socio'

class CustomUserAdmin(UserAdmin):
    """Extiende el admin de User para incluir Socio"""
    inlines = (SocioInline,)
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

# Desregistrar el User admin original y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(NivelAcceso)
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('id', 'cedula', 'user', 'tipo_usuario', 'estado_socio', 'nivel_acceso')
    list_filter = ('tipo_usuario', 'estado_socio', 'nivel_acceso')
    search_fields = ('cedula', 'user__username', 'user__email')
    raw_id_fields = ('user',)

    