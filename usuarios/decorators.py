from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def es_taller(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = getattr(request.user, 'perfil', None)
        if perfil and perfil.tipo_usuario == 'taller':
            return view_func(request, *args, **kwargs)
        return redirect('dashboard')
    return _wrapped_view

def usuario_tipo_requerido(*tipos_permitidos):
    """
    Permite acceso a los tipos de usuario indicados o a superusuarios.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or (hasattr(request.user, 'perfil') and request.user.perfil.tipo_usuario in tipos_permitidos):
                return view_func(request, *args, **kwargs)
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('dashboard')
        return _wrapped_view
    return decorator