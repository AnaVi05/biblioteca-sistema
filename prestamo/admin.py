from django.contrib import admin
from .models import Prestamo

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id', 'socio', 'fecha_prestamo', 'fecha_vencimiento', 'estado', 'dias_atraso')
    list_filter = ('estado', 'fecha_prestamo', 'fecha_vencimiento')
    search_fields = ('socio__cedula', 'socio__user__first_name', 'socio__user__last_name')
    list_editable = ('estado',)
    readonly_fields = ('fecha_prestamo', 'dias_atraso')
    
    fieldsets = (
        ('Datos del préstamo', {
            'fields': ('socio', 'fecha_prestamo', 'fecha_vencimiento')
        }),
        ('Devolución', {
            'fields': ('fecha_devolucion_real', 'estado', 'observaciones')
        }),
        ('Información adicional', {
            'fields': ('dias_atraso',),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['marcar_como_devuelto', 'marcar_como_extraviado']
    
    def marcar_como_devuelto(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            estado='DEVUELTO',
            fecha_devolucion_real=timezone.now().date()
        )
    marcar_como_devuelto.short_description = "Marcar préstamos como devueltos"
    
    def marcar_como_extraviado(self, request, queryset):
        queryset.update(estado='EXTRAVIADO')
    marcar_como_extraviado.short_description = "Marcar préstamos como extraviados"