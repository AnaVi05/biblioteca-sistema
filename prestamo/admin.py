from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.urls import path
from django.shortcuts import redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Prestamo, Reserva, Multa, Configuracion
from catalogo.models import Libro, Autor, Editorial, Categoria, Ejemplar
from usuario.models import Socio, NivelAcceso


# ========== VISTA DE CONFIGURACIÓN ==========
@staff_member_required
def configuracion_view(request):
    """Vista de configuración del sistema"""
    
    # Obtener o crear configuración
    config, created = Configuracion.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        try:
            config.dias_maximos_prestamo = int(request.POST.get('dias_maximos_prestamo', 5))
            config.valor_multa_por_dia = float(request.POST.get('valor_multa_por_dia', 1000))
            config.dias_expiracion_reserva = int(request.POST.get('dias_expiracion_reserva', 3))
            config.reservas_automaticas = request.POST.get('reservas_automaticas') == 'on'
            config.notificaciones_vencimiento = request.POST.get('notificaciones_vencimiento') == 'on'
            config.save()
            messages.success(request, 'Configuración actualizada exitosamente')
        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
        return redirect('/admin/configuracion/')
    
    context = {
        'config': config,
        'title': 'Configuración del Sistema',
    }
    return render(request, 'admin/configuracion.html', context)


# ========== VISTA DEL DASHBOARD ==========
@staff_member_required
def admin_dashboard(request):
    from django.contrib.auth.models import User
    from catalogo.models import Libro
    from prestamo.models import Prestamo, Multa
    from django.utils import timezone
    
    hoy = timezone.now().date()
    
    total_usuarios = User.objects.count()
    total_libros = Libro.objects.count()
    prestamos_mes = Prestamo.objects.filter(
        fecha_prestamo__month=hoy.month,
        fecha_prestamo__year=hoy.year
    ).count()
    incidencias = Multa.objects.filter(estado='PENDIENTE').count()
    
    # Actividad reciente
    actividades = []
    
    from usuario.models import Socio
    ultimos_usuarios = User.objects.order_by('-date_joined')[:2]
    for u in ultimos_usuarios:
        actividades.append({
            'titulo': 'Nuevo usuario registrado',
            'descripcion': f'{u.get_full_name()} - Usuario',
            'tiempo': u.date_joined
        })
    
    ultimos_libros = Libro.objects.order_by('-id')[:2]
    for l in ultimos_libros:
        actividades.append({
            'titulo': 'Libro agregado',
            'descripcion': f'"{l.titulo}"',
            'tiempo': None
        })
    
    context = {
        'total_usuarios': total_usuarios,
        'total_libros': total_libros,
        'prestamos_mes': prestamos_mes,
        'incidencias': incidencias,
        'actividades': actividades,
        'title': 'Panel de Control',
    }
    return render(request, 'admin/index.html', context)


# ========== ADMIN PERSONALIZADO ==========
class CustomAdminSite(AdminSite):
    site_header = "📚 Biblioteca - Panel de Administración"
    site_title = "Administración Biblioteca"
    index_title = "Panel de Control"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(admin_dashboard), name='index'),
            path('configuracion/', self.admin_view(configuracion_view), name='configuracion'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        return redirect('/admin/')


# Crear instancia del admin personalizado
admin_site = CustomAdminSite(name='admin')


# ========== REGISTRAR MODELOS ==========

@admin.register(Prestamo, site=admin_site)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ['id', 'socio', 'ejemplar', 'fecha_prestamo', 'fecha_vencimiento', 'estado']
    list_filter = ['estado', 'fecha_prestamo']
    search_fields = ['socio__user__username', 'socio__user__first_name', 'socio__user__last_name', 'ejemplar__codigo_inventario']
    readonly_fields = ['fecha_prestamo']
    list_per_page = 20
    date_hierarchy = 'fecha_prestamo'
    
    fieldsets = (
        ('Información del Préstamo', {
            'fields': ('socio', 'ejemplar')
        }),
        ('Fechas', {
            'fields': ('fecha_prestamo', 'fecha_vencimiento', 'fecha_devolucion_real')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
    )


@admin.register(Reserva, site=admin_site)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['id', 'socio', 'libro', 'fecha_reserva', 'fecha_expiracion', 'estado']
    list_filter = ['estado', 'fecha_reserva']
    search_fields = ['socio__user__username', 'libro__titulo']
    list_per_page = 20


@admin.register(Multa, site=admin_site)
class MultaAdmin(admin.ModelAdmin):
    list_display = ['id', 'prestamo', 'dias_atraso', 'monto_total', 'estado', 'fecha_generacion']
    list_filter = ['estado', 'fecha_generacion']
    search_fields = ['prestamo__socio__user__username']
    list_per_page = 20
    readonly_fields = ['fecha_generacion', 'dias_atraso', 'monto_total']
    
    fieldsets = (
        ('Información de la Multa', {
            'fields': ('prestamo',)
        }),
        ('Cálculo', {
            'fields': ('dias_atraso', 'monto_base', 'monto_por_dia', 'monto_total')
        }),
        ('Pago', {
            'fields': ('estado', 'fecha_pago', 'comprobante_pago')
        }),
    )


@admin.register(Configuracion, site=admin_site)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ['id', 'dias_maximos_prestamo', 'valor_multa_por_dia', 'dias_expiracion_reserva', 'fecha_actualizacion']
    readonly_fields = ['fecha_actualizacion']
    
    fieldsets = (
        ('Parámetros de Préstamos', {
            'fields': ('dias_maximos_prestamo', 'valor_multa_por_dia')
        }),
        ('Parámetros de Reservas', {
            'fields': ('dias_expiracion_reserva', 'reservas_automaticas')
        }),
        ('Notificaciones', {
            'fields': ('notificaciones_vencimiento',)
        }),
        ('Información', {
            'fields': ('fecha_actualizacion',)
        }),
    )


@admin.register(Socio, site=admin_site)
class SocioAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'cedula', 'tipo_usuario', 'estado_socio', 'fecha_registro']
    list_filter = ['estado_socio', 'tipo_usuario']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'cedula']
    list_per_page = 20
    readonly_fields = ['fecha_registro']
    
    fieldsets = (
        ('Datos del Usuario', {
            'fields': ('user', 'cedula', 'telefono', 'direccion', 'carrera')
        }),
        ('Clasificación', {
            'fields': ('tipo_usuario', 'estado_socio', 'nivel_acceso')
        }),
        ('Registro', {
            'fields': ('fecha_registro',)
        }),
    )


@admin.register(Libro, site=admin_site)
class LibroAdmin(admin.ModelAdmin):
    list_display = ['id', 'isbn', 'titulo', 'editorial', 'categoria', 'cantidad_total', 'inventario_disponible']
    list_filter = ['editorial', 'categoria']
    search_fields = ['titulo', 'isbn']
    list_per_page = 20
    # IMPORTANTE: Elimina filter_horizontal = ['autores']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('isbn', 'titulo', 'anio_publicacion', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('editorial', 'categoria')  # Elimina 'autores'
        }),
        ('Inventario', {
            'fields': ('cantidad_total', 'inventario_disponible', 'imagen')
        }),
    )


@admin.register(Ejemplar, site=admin_site)
class EjemplarAdmin(admin.ModelAdmin):
    list_display = ['id', 'codigo_inventario', 'libro', 'estado_fisico', 'disponibilidad', 'ubicacion']
    list_filter = ['estado_fisico', 'disponibilidad']
    search_fields = ['codigo_inventario', 'libro__titulo']
    list_per_page = 20


@admin.register(Autor, site=admin_site)
class AutorAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'apellido']
    search_fields = ['nombre', 'apellido']
    list_per_page = 20


@admin.register(Editorial, site=admin_site)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']
    list_per_page = 20


@admin.register(Categoria, site=admin_site)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']
    list_per_page = 20


@admin.register(NivelAcceso, site=admin_site)
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']
    list_per_page = 20


@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_per_page = 20
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Biblioteca', {
            'fields': (),
        }),
    )


@admin.register(Group, site=admin_site)
class CustomGroupAdmin(GroupAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 20
