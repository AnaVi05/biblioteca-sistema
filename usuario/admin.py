from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from .models import NivelAcceso, Socio


class SocioInline(admin.StackedInline):
    model = Socio
    can_delete = False
    verbose_name_plural = 'Datos de Socio'

    fields = ('cedula', 'telefono', 'direccion', 'carrera', 'tipo_usuario', 'estado_socio', 'nivel_acceso', 'motivo_inhabilitacion')


class CustomUserAdmin(UserAdmin):
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
    list_display = ('cedula', 'user', 'tipo_usuario', 'estado_socio', 'motivo_corto', 'boton_inhabilitar')
    list_filter = ('tipo_usuario', 'estado_socio')
    search_fields = ('cedula', 'user__username', 'user__email', 'motivo_inhabilitacion')
    raw_id_fields = ('user',)

    fields = ('user', 'cedula', 'telefono', 'direccion', 'carrera',
              'tipo_usuario', 'estado_socio', 'nivel_acceso', 'motivo_inhabilitacion')

    def motivo_corto(self, obj):
        if obj.motivo_inhabilitacion:
            if len(obj.motivo_inhabilitacion) > 50:
                return obj.motivo_inhabilitacion[:50] + '...'
            return obj.motivo_inhabilitacion
        return '-'
    motivo_corto.short_description = 'Motivo'

    def boton_inhabilitar(self, obj):
        if obj.estado_socio == 'activo':
            url = reverse('admin:usuario_socio_inhabilitar', args=[obj.id])
            return format_html('<a href="{}" style="background: #dc2626; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Inhabilitar</a>', url)
        else:
            url = reverse('admin:usuario_socio_habilitar', args=[obj.id])
            return format_html('<a href="{}" style="background: #16a34a; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Habilitar</a>', url)
    boton_inhabilitar.short_description = 'Acción'

    def save_model(self, request, obj, form, change):
        if 'estado_socio' in form.changed_data and obj.estado_socio == 'inhabilitado':
            motivo = form.cleaned_data.get('motivo_inhabilitacion')
            if not motivo:
                messages.error(request, '❌ Debes especificar un motivo para inhabilitar al socio.')
                return
        super().save_model(request, obj, form, change)