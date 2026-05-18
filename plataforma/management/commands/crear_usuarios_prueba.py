from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from plataforma.models import Tecnico, Proveedor


USUARIOS = [
    {
        "tipo": "admin",
        "username": "admin",
        "email": "admin@repuestos.com",
        "password": "admin1234",
        "first_name": "Admin",
        "last_name": "Sistema",
        "is_superuser": True,
        "is_staff": True,
    },
    {
        "tipo": "tecnico",
        "username": "tecnico_prueba",
        "email": "tecnico@repuestos.com",
        "password": "tecnico1234",
        "first_name": "Carlos",
        "last_name": "Rodríguez",
        "perfil": {
            "cuit": "20-12345678-9",
            "especialidad": "mecanica_automotriz",
            "telefono": "011-4567-8901",
            "ubicacion": "Buenos Aires, CABA",
            "estado": "aprobado",
            "is_approved": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "proveedor_prueba",
        "email": "proveedor@repuestos.com",
        "password": "proveedor1234",
        "first_name": "Laura",
        "last_name": "Martínez",
        "perfil": {
            "cuit": "30-98765432-1",
            "nombre_negocio": "Repuestos del Sur",
            "direccion": "Av. Corrientes 1234, CABA",
            "rubro": "mecanica_automotriz",
            "horarios": "Lun-Vie 09:00-18:00",
            "estado": "aprobado",
            "is_approved": True,
        },
    },
]


class Command(BaseCommand):
    help = "Crea 3 usuarios de prueba: admin, técnico y proveedor"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los usuarios existentes antes de crearlos",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            usernames = [u["username"] for u in USUARIOS]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(self.style.WARNING(f"  {deleted} usuarios eliminados."))

        for datos in USUARIOS:
            tipo = datos["tipo"]
            username = datos["username"]

            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"  [{tipo}] '{username}' ya existe, omitiendo."))
                continue

            user = User.objects.create_user(
                username=username,
                email=datos["email"],
                password=datos["password"],
                first_name=datos["first_name"],
                last_name=datos["last_name"],
                is_superuser=datos.get("is_superuser", False),
                is_staff=datos.get("is_staff", False),
            )

            if tipo == "tecnico":
                Tecnico.objects.create(usuario=user, **datos["perfil"])
            elif tipo == "proveedor":
                Proveedor.objects.create(usuario=user, **datos["perfil"])

            self.stdout.write(self.style.SUCCESS(f"  [{tipo}] '{username}' creado OK"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Usuarios de prueba listos:"))
        self.stdout.write("  admin         / admin1234     (superusuario)")
        self.stdout.write("  tecnico_prueba  / tecnico1234   (técnico aprobado)")
        self.stdout.write("  proveedor_prueba / proveedor1234 (proveedor aprobado)")
