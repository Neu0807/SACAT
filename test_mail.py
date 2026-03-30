import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Configuración necesaria para usar Django fuera del servidor
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sacat.settings') # <--- CAMBIA 'tu_proyecto' POR EL NOMBRE DE TU CARPETA DE SETTINGS
django.setup()

try:
    print("🚀 Intentando enviar correo desde SACAT...")
    enviado = send_mail(
        'Prueba de Fuego SACAT ⚡',
        '¡Epa Jade! Si lees esto, el sistema ya está conectado con Gmail oficialmente.',
        settings.EMAIL_HOST_USER,
        ['mahocolina@gmail.com'], # <--- PON TU CORREO AQUÍ
        fail_silently=False,
    )
    if enviado:
        print("✅ ¡ÉXITO! El correo salió volando. Revisa tu bandeja.")
except Exception as e:
    print(f"❌ ERROR: No se pudo enviar. Detalles: {e}")