from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Socio, NivelAcceso

def registrar_usuario(request):
    if request.method == 'POST':
        # Obtener datos
        nombre_completo = request.POST.get('nombre_completo')
        email = request.POST.get('email')
        username = request.POST.get('username')
        cedula = request.POST.get('cedula')
        tipo_usuario = request.POST.get('tipo_usuario')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validar que no sea administrativo
        if tipo_usuario == 'administrativo':
            messages.error(request, 'El personal administrativo debe ser creado por el administrador')
            return render(request, 'registration/registro.html')
        
        # Validar contraseñas
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'registration/registro.html')
        
        # Validar usuario existente
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe')
            return render(request, 'registration/registro.html')
        
        # Validar email existente
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado')
            return render(request, 'registration/registro.html')
        
        # Validar cédula existente
        if Socio.objects.filter(cedula=cedula).exists():
            messages.error(request, 'La cédula ya está registrada')
            return render(request, 'registration/registro.html')
        
        # Separar nombre completo
        nombres = nombre_completo.split()
        first_name = nombres[0] if nombres else ''
        last_name = ' '.join(nombres[1:]) if len(nombres) > 1 else ''
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        
        # Obtener nivel de acceso por defecto
        nivel_usuario = NivelAcceso.objects.get(nombre='Usuario')
        
        # Crear socio
        Socio.objects.create(
            user=user,
            cedula=cedula,
            tipo_usuario=tipo_usuario,
            estado_socio='activo',
            nivel_acceso=nivel_usuario
        )
        
        messages.success(request, '¡Registro exitoso! Ya puedes iniciar sesión.')
        return redirect('login')
    
    return render(request, 'registration/registro.html')