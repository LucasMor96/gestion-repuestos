ESTADO_USUARIO_CHOICES = [
    ('pendiente', 'Pendiente'),
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
    ('suspendido', 'Suspendido'),
]

RUBROS_CHOICES = [
    ('mecanica_automotriz', 'Mecánica Automotriz'),
    ('tecnico_computadoras', 'Técnico de Computadoras'),
]

ESTRELLAS_CHOICES = [(i, f"{i} estrella{'s' if i != 1 else ''}") for i in range(1, 6)]
