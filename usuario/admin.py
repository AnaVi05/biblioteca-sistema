from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import NivelAcceso, Socio


class SocioInline(admin.StackedInline):
    """Para mostrar Socio dentro del admin de User"""
    model = Socio
    can_delete = False
    verbose_name_plural = 'Datos de Socio'
    
    fields = ('cedula', 'telefono', 'direccion', 'carrera', 'tipo_usuario', 'estado_socio', 'nivel_acceso', 'motivo_inhabilitacion')


class CustomUserAdmin(UserAdmin):
    """Extiende el admin de User para incluir Socio"""
    inlines = (SocioInline,)
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(NivelAcceso)
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('cedula', 'user', 'tipo_usuario', 'estado_socio', 'motivo_corto')
    list_filter = ('tipo_usuario', 'estado_socio')
    search_fields = ('cedula', 'user__username', 'user__email', 'motivo_inhabilitacion')
    raw_id_fields = ('user',)
    
    # Todos los campos visibles en el formulario
    fields = ('user', 'cedula', 'telefono', 'direccion', 'carrera', 
              'tipo_usuario', 'estado_socio', 'nivel_acceso', 'motivo_inhabilitacion')
    
    def motivo_corto(self, obj):
        if obj.motivo_inhabilitacion:
            return obj.motivo_inhabilitacion[:50]
        return '-'
    motivo_corto.short_description = 'Motivo'
    
    def save_model(self, request, obj, form, change):
        """Validar que haya motivo al inhabilitar"""
        if 'estado_socio' in form.changed_data and obj.estado_socio == 'inhabilitado':
            motivo = form.cleaned_data.get('motivo_inhabilitacion')
            if not motivo:
                messages.error(request, '❌ Debes especificar un motivo para inhabilitar al socio.')
                return
        super().save_model(request, obj, form, change)