from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def almacenamiento_moderacion():
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def ruta_imagen_moderacion(instance, filename):
    return f'moderacion/{uuid4().hex}{instance.extension}'
