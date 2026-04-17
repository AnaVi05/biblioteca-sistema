from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.urls import path
from django.shortcuts import redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django import forms
from .models import Prestamo, Reserva, Multa, Configuracion
from catalogo.models import Libro, Autor, Editorial, Categoria, Ejemplar
from usuario.models import Socio, NivelAcceso
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect


# ========== FORMULARIO PERSONALIZADO PARA LIBRO CON EJEMPLAR ==========
class LibroAdminForm(forms.ModelForm):
    """Formulario personalizado para crear libro con ejemplar"""
    
    codigo_inventario = forms.CharField(
        required=False,
        label="Código de inventario",
        help_text="Déjalo vacío para que se genere automáticamente"
    )
    estado_fisico = forms.ChoiceField(
        choices=Ejemplar.ESTADO_FISICO_CHOICES,
        required=False,
        initial='BUENO',
        label="Estado físico"
    )
    disponibilidad = forms.ChoiceField(
        choices=Ejemplar.DISPONIBILIDAD_CHOICES,
        required=False,
        initial='DISPONIBLE',
        label="Disponibilidad"
    )
    ubicacion = forms.CharField(
        required=False,
        label="Ubicación",
        help_text="Ej: Estante A3, Sección 5"
    )
    
    class Meta:
        model = Libro
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        cantidad_total = cleaned_data.get('cantidad_total', 0)
        inventario_disponible = cleaned_data.get('inventario_disponible', 0)
        
        # Validación para libro nuevo
        if not self.instance.pk:
            if cantidad_total == 0:
                self.add_error('cantidad_total', '❌ Un libro nuevo debe tener al menos 1 ejemplar. Completa la sección "Ejemplar Inicial" o cambia la cantidad total a 1.')
            if inventario_disponible == 0:
                self.add_error('inventario_disponible', '❌ Un libro nuevo debe tener al menos 1 ejemplar disponible.')
        
        # Validación: disponible no puede ser mayor que total
        if inventario_disponible > cantidad_total:
            self.add_error('inventario_disponible', '❌ Los ejemplares disponibles no pueden ser mayores al total')
        
        return cleaned_data
    
    def save(self, commit=True):
        libro = super().save(commit=False)
        
        # Si es un libro nuevo, establecer cantidades en 1
        if not self.instance.pk:
            libro.cantidad_total = 1
            libro.inventario_disponible = 1
        
        if commit:
            libro.save()
            
            # Solo crear ejemplar si es un libro nuevo
            if not self.instance.pk:
                codigo = self.cleaned_data.get('codigo_inventario')
                if not codigo:
                    codigo = f"AUTO-{libro.id:04d}"
                
                Ejemplar.objects.create(
                    libro=libro,
                    codigo_inventario=codigo,
                    estado_fisico=self.cleaned_data.get('estado_fisico', 'BUENO'),
                    disponibilidad=self.cleaned_data.get('disponibilidad', 'DISPONIBLE'),
                    ubicacion=self.cleaned_data.get('ubicacion', '')
                )
                
                # Actualizar cantidades reales
                libro.cantidad_total = Ejemplar.objects.filter(libro=libro).count()
                libro.inventario_disponible = Ejemplar.objects.filter(libro=libro, disponibilidad='DISPONIBLE').count()
                libro.save()
        
        return libro


# ========== VISTA DEL DASHBOARD ==========
def admin_dashboard(request):
    """Dashboard personalizado para el administrador"""
    from django.contrib.auth.models import User
    from catalogo.models import Libro
    from prestamo.models import Prestamo, Multa
    from django.utils import timezone
    from usuario.models import Socio
    
    hoy = timezone.now().date()
    
    total_usuarios = User.objects.count()
    total_libros = Libro.objects.count()
    prestamos_mes = Prestamo.objects.filter(
        fecha_prestamo__month=hoy.month,
        fecha_prestamo__year=hoy.year
    ).count()
    incidencias = Multa.objects.filter(estado='PENDIENTE').count()
    
    actividades = []
    
    ultimos_usuarios = User.objects.order_by('-date_joined')[:3]
    for u in ultimos_usuarios:
        try:
            tipo = u.socio.tipo_usuario if hasattr(u, 'socio') else 'Usuario'
        except:
            tipo = 'Usuario'
        actividades.append({
            'titulo': 'Nuevo usuario registrado',
            'descripcion': f'{u.get_full_name()} - Rol: {tipo}',
            'tiempo': u.date_joined
        })
    
    ultimos_libros = Libro.objects.order_by('-id')[:3]
    for l in ultimos_libros:
        actividades.append({
            'titulo': 'Libro agregado',
            'descripcion': f'"{l.titulo}"',
            'tiempo': None
        })
    
    ultimos_prestamos = Prestamo.objects.select_related('socio__user', 'ejemplar__libro').order_by('-fecha_prestamo')[:2]
    for p in ultimos_prestamos:
        actividades.append({
            'titulo': 'Préstamo registrado',
            'descripcion': f'{p.socio.user.get_full_name()} - "{p.ejemplar.libro.titulo}"',
            'tiempo': p.fecha_prestamo
        })
    
    context = {
        'total_usuarios': total_usuarios,
        'total_libros': total_libros,
        'prestamos_mes': prestamos_mes,
        'incidencias': incidencias,
        'actividades': actividades[:6],
        'title': 'Panel de Control',
    }
    return render(request, 'admin/index.html', context)


# ========== VISTA DE CONFIGURACIÓN ==========
@staff_member_required
def configuracion_view(request):
    """Vista de configuración del sistema"""
    
    config, created = Configuracion.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        try:
            config.dias_maximos_prestamo = int(request.POST.get('dias_maximos_prestamo', 5))
            config.valor_multa_por_dia = float(request.POST.get('valor_multa_por_dia', 1000))
            config.dias_expiracion_reserva = int(request.POST.get('dias_expiracion_reserva', 3))
            config.reservas_automaticas = request.POST.get('reservas_automaticas') == 'on'
            config.notificaciones_vencimiento = request.POST.get('notificaciones_vencimiento') == 'on'
            config.save()
            messages.success(request, '✅ Configuración actualizada exitosamente')
        except Exception as e:
            messages.error(request, f'❌ Error al guardar: {str(e)}')
        return redirect('/admin/configuracion/')
    
    context = {
        'config': config,
        'title': 'Configuración del Sistema',
    }
    return render(request, 'admin/configuracion.html', context)


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
@admin.register(Libro, site=admin_site)
class LibroAdmin(admin.ModelAdmin):
    form = LibroAdminForm
    list_display = ['id', 'isbn', 'titulo', 'editorial', 'categoria', 'cantidad_total', 'inventario_disponible', 'estado_activo', 'acciones']
    list_filter = ['editorial', 'categoria', 'activo']
    search_fields = ['titulo', 'isbn']
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('isbn', 'titulo', 'anio_publicacion', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('editorial', 'categoria')
        }),
        ('Inventario', {
            'fields': ('cantidad_total', 'inventario_disponible', 'imagen')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Ejemplar Inicial', {
            'fields': ('codigo_inventario', 'estado_fisico', 'disponibilidad', 'ubicacion'),
            'classes': ('collapse',),
            'description': 'Completa estos campos para crear el primer ejemplar automáticamente'
        }),
    )
    
    def estado_activo(self, obj):
        if obj.activo:
            return "✓ Activo"
        else:
            return "✗ Inactivo"
    estado_activo.short_description = 'Estado'
    
    def acciones(self, obj):
        if obj.activo:
            return format_html(
                '<a class="btn-dar-baja" href="{}">Dar de baja</a>',
                reverse('admin:catalogo_libro_dar_baja', args=[obj.id])
            )
        else:
            return format_html(
                '<a class="btn-dar-alta" href="{}">Dar de alta</a>',
                reverse('admin:catalogo_libro_dar_alta', args=[obj.id])
            )
    acciones.short_description = 'Acciones'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dar-baja/<int:libro_id>/', self.dar_baja_view, name='catalogo_libro_dar_baja'),
            path('dar-alta/<int:libro_id>/', self.dar_alta_view, name='catalogo_libro_dar_alta'),
        ]
        return custom_urls + urls
    
    def dar_baja_view(self, request, libro_id):
        from catalogo.models import Libro
        libro = Libro.objects.get(id=libro_id)
        libro.activo = False
        libro.save()
        self.message_user(request, f'✅ Libro "{libro.titulo}" dado de baja correctamente.', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:catalogo_libro_changelist'))
    
    def dar_alta_view(self, request, libro_id):
        from catalogo.models import Libro
        libro = Libro.objects.get(id=libro_id)
        libro.activo = True
        libro.save()
        self.message_user(request, f'✅ Libro "{libro.titulo}" dado de alta correctamente.', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:catalogo_libro_changelist'))
    
    def delete_model(self, request, obj):
        self.message_user(request, f'❌ No se puede eliminar el libro "{obj.titulo}". Use "Dar de baja" en su lugar.', messages.ERROR)
    
    def delete_queryset(self, request, queryset):
        self.message_user(request, f'❌ No se puede eliminar libros. Use "Dar de baja" en su lugar.', messages.ERROR)
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


@admin.register(Group, site=admin_site)
class CustomGroupAdmin(GroupAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 20