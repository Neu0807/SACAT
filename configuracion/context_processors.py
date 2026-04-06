# configuracion/context_processors.py
from .models import IdentidadInstitucional

def info_institucion(request):
    # Agarra el primer registro que consiga (el único que hay)
    identidad = IdentidadInstitucional.objects.first()
    return {
        'identidad': identidad
    }