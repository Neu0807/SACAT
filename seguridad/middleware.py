from django.shortcuts import redirect
from django.urls import reverse

class ForzarCambioClaveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Si debe cambiar clave y NO está ya en la página de cambio o saliendo
            rutas_permitidas = [reverse('cambiar_clave_obligatorio'), reverse('salir_sistema')]
            
            if request.user.requiere_cambio_clave and request.path not in rutas_permitidas:
                return redirect('cambiar_clave_obligatorio')
        
        return self.get_response(request)