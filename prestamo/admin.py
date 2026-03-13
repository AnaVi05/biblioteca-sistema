from django.contrib import admin
from .models import Prestamo,Reserva

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista
    list_display = (
        'id',
        'socio',
        'codigo_ejemplar',          # Muestra el código del ejemplar
        'fecha_prestamo',
        'fecha_vencimiento',
        'estado',
        'dias_atraso'
    )

    # Filtros laterales
    list_filter = ('estado', 'fecha_prestamo', 'fecha_vencimiento')

    # Campos por los que se puede buscar
    search_fields = (
        'socio__cedula',
        'socio__user__first_name',
        'socio__user__last_name',
        'ejemplar__codigo_inventario'   # Búsqueda por código de ejemplar
    )

    # Campos que se pueden editar directamente desde la lista
    list_editable = ('estado',)

    # Campos de solo lectura
    readonly_fields = ('fecha_prestamo', 'dias_atraso')

    # Organización del formulario de edición
    fieldsets = (
        ('Datos del préstamo', {
            'fields': ('socio', 'ejemplar', 'fecha_prestamo', 'fecha_vencimiento')
        }),
        ('Devolución', {
            'fields': ('fecha_devolucion_real', 'estado', 'observaciones')
        }),
        ('Información adicional', {
            'fields': ('dias_atraso',),
            'classes': ('collapse',),
        }),
    )

    # Acciones personalizadas
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

    # Método para mostrar el código del ejemplar
    def codigo_ejemplar(self, obj):
        if obj.ejemplar:
            return obj.ejemplar.codigo_inventario
        return "-"
    codigo_ejemplar.short_description = "Código ejemplar"
    codigo_ejemplar.admin_order_field = 'ejemplar__codigo_inventario'  # Permitir ordenar

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'socio', 'libro', 'fecha_reserva', 'fecha_expiracion', 'estado', 'orden_prioridad')
    list_filter = ('estado', 'fecha_reserva')
    search_fields = ('socio__cedula', 'socio__user__first_name', 'libro__titulo')
    list_editable = ('estado', 'orden_prioridad')
    readonly_fields = ('fecha_reserva',)
    
    fieldsets = (
        ('Datos de la reserva', {
            'fields': ('socio', 'libro', 'fecha_reserva', 'fecha_expiracion')
        }),
        ('Estado y prioridad', {
            'fields': ('estado', 'orden_prioridad', 'ejemplar_asignado')
        }),
    )