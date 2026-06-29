from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from time import sleep
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from plataforma.models import Pedido, Producto, Proveedor, Tecnico


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
        "last_name": "Rodriguez",
        "perfil": {
            "cuit": "20-12345678-9",
            "especialidad": "mecanica_automotriz",
            "telefono": "011-4567-8901",
            "ubicacion": "Buenos Aires, CABA",
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "tecnico",
        "username": "tecnico_rawson",
        "email": "tecnico.rawson@repuestos.com",
        "password": "tecnico1234",
        "first_name": "Sofia",
        "last_name": "Gomez",
        "perfil": {
            "cuit": "27-23568974-3",
            "especialidad": "mecanica_automotriz",
            "telefono": "280-445-0198",
            "ubicacion": "Rawson, Chubut",
            "latitud": -43.3002,
            "longitud": -65.1023,
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "proveedor_prueba",
        "email": "proveedor@repuestos.com",
        "password": "proveedor1234",
        "first_name": "Laura",
        "last_name": "Martinez",
        "perfil": {
            "cuit": "30-98765432-1",
            "nombre_negocio": "Repuestos del Sur",
            "direccion": "Av. Corrientes 1234, CABA",
            "rubro": "mecanica_automotriz",
            "horarios": "Lun-Vie 09:00-18:00",
            "banco_transferencia": "Banco Nacion",
            "titular_transferencia": "Repuestos del Sur",
            "cbu_transferencia": "0110000000000000000001",
            "alias_transferencia": "REPUESTOS.SUR",
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "repuestos_rawson",
        "email": "ventas@repuestosrawson.com",
        "password": "proveedor1234",
        "first_name": "Marcos",
        "last_name": "Pereyra",
        "perfil": {
            "cuit": "30-17456328-4",
            "nombre_negocio": "Repuestos Rawson Centro",
            "direccion": "Av. San Martin 615, Rawson, Chubut",
            "rubro": "mecanica_automotriz",
            "horarios": "Lun-Vie 08:30-18:30 / Sab 09:00-13:00",
            "banco_transferencia": "Banco Chubut",
            "titular_transferencia": "Repuestos Rawson Centro",
            "cbu_transferencia": "0830000000000000000002",
            "alias_transferencia": "RAWSON.REPUESTOS",
            "latitud": -43.2994,
            "longitud": -65.1018,
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "autopartes_chubut",
        "email": "contacto@autoparteschubut.com",
        "password": "proveedor1234",
        "first_name": "Valeria",
        "last_name": "Torres",
        "perfil": {
            "cuit": "30-28473916-7",
            "nombre_negocio": "Autopartes Chubut",
            "direccion": "Mariano Moreno 842, Rawson, Chubut",
            "rubro": "mecanica_automotriz",
            "horarios": "Lun-Sab 09:00-17:00",
            "banco_transferencia": "Banco Galicia",
            "titular_transferencia": "Autopartes Chubut",
            "cbu_transferencia": "0070000000000000000003",
            "alias_transferencia": "AUTOPARTES.CHUBUT",
            "latitud": -43.3031,
            "longitud": -65.0949,
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "tecno_rawson",
        "email": "soporte@tecnorawson.com",
        "password": "proveedor1234",
        "first_name": "Nicolas",
        "last_name": "Arias",
        "perfil": {
            "cuit": "30-31457892-2",
            "nombre_negocio": "Tecno Rawson Insumos",
            "direccion": "Belgrano 325, Rawson, Chubut",
            "rubro": "tecnico_computadoras",
            "horarios": "Lun-Vie 10:00-19:00",
            "banco_transferencia": "Mercado Pago",
            "titular_transferencia": "Tecno Rawson Insumos",
            "cbu_transferencia": "0000003100000000000004",
            "alias_transferencia": "TECNO.RAWSON",
            "latitud": -43.2982,
            "longitud": -65.1062,
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
    {
        "tipo": "proveedor",
        "username": "electronica_puerto",
        "email": "ventas@electronicapuerto.com",
        "password": "proveedor1234",
        "first_name": "Carolina",
        "last_name": "Benitez",
        "perfil": {
            "cuit": "30-41852679-5",
            "nombre_negocio": "Electronica Puerto",
            "direccion": "Luis Costa 1120, Rawson, Chubut",
            "rubro": "tecnico_computadoras",
            "horarios": "Lun-Vie 09:30-18:00 / Sab 10:00-13:00",
            "banco_transferencia": "Banco Santander",
            "titular_transferencia": "Electronica Puerto",
            "cbu_transferencia": "0720000000000000000005",
            "alias_transferencia": "ELECTRONICA.PUERTO",
            "latitud": -43.2949,
            "longitud": -65.1098,
            "estado": "aprobado",
            "is_approved": True,
            "email_confirmed": True,
        },
    },
]


PRODUCTOS_DEMO = {
    "proveedor_prueba": [
        ("Filtro de aceite Wega", "Filtro para autos nafteros y diesel livianos.", "WO-120", "mecanica_automotriz", "9800.00", 18),
        ("Pastillas de freno Bosch", "Juego delantero para vehiculos compactos.", "BP-452", "mecanica_automotriz", "42500.00", 10),
        ("Bateria 12V Moura", "Bateria 75 Ah con garantia.", "M75GD", "mecanica_automotriz", "148000.00", 6),
    ],
    "repuestos_rawson": [
        ("Kit distribucion Renault", "Correa, tensor y ruleman para motores 1.6.", "KD-R16", "mecanica_automotriz", "112000.00", 7),
        ("Amortiguador delantero Corven", "Unidad delantera para utilitarios livianos.", "AC-3012", "mecanica_automotriz", "86500.00", 12),
        ("Bujias NGK x4", "Juego de cuatro bujias para motor naftero.", "BKR6E", "mecanica_automotriz", "23800.00", 24),
        ("Liquido refrigerante 5L", "Refrigerante organico listo para usar.", "REF-5L", "mecanica_automotriz", "16500.00", 20),
    ],
    "autopartes_chubut": [
        ("Radiador Peugeot 206", "Radiador de aluminio con deposito plastico.", "RAD-206", "mecanica_automotriz", "132500.00", 5),
        ("Optica derecha Gol Trend", "Optica halogena lado acompanante.", "OPT-GT-D", "mecanica_automotriz", "74500.00", 8),
        ("Sensor MAP Fiat", "Sensor de presion para inyeccion electronica.", "MAP-FIAT", "mecanica_automotriz", "38900.00", 9),
        ("Embrague completo Corsa", "Placa, disco y ruleman.", "EMB-COR", "mecanica_automotriz", "158000.00", 4),
    ],
    "tecno_rawson": [
        ("SSD Kingston 480GB", "Disco solido SATA para notebooks y PCs.", "SA400-480", "tecnico_computadoras", "62000.00", 15),
        ("Memoria DDR4 8GB", "Modulo 2666 MHz para escritorio.", "DDR4-8-2666", "tecnico_computadoras", "35500.00", 18),
        ("Fuente ATX 600W", "Fuente certificada para PC de escritorio.", "ATX-600", "tecnico_computadoras", "58500.00", 11),
        ("Pasta termica Arctic", "Jeringa de 4 gramos.", "MX4-4G", "tecnico_computadoras", "12400.00", 30),
    ],
    "electronica_puerto": [
        ("Cargador notebook universal", "Cargador 90W con puntas intercambiables.", "CH-90U", "tecnico_computadoras", "46500.00", 10),
        ("Pantalla notebook 15.6", "Panel LED slim 30 pines.", "LED-156", "tecnico_computadoras", "121000.00", 6),
        ("Teclado notebook Lenovo", "Teclado espanol para linea IdeaPad.", "KBD-LEN", "tecnico_computadoras", "39500.00", 7),
        ("Cooler CPU universal", "Cooler para gabinetes y reparaciones.", "FAN-120", "tecnico_computadoras", "9800.00", 22),
    ],
}


PRODUCTOS_DEMO_IMAGENES = {
    "Filtro de aceite Wega": (
        "filtro-aceite-wega.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/52/Bosch_Oil_Filter.JPG",
    ),
    "Pastillas de freno Bosch": (
        "pastillas-freno-bosch.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/76/Brake_pads.JPG",
    ),
    "Bateria 12V Moura": (
        "bateria-12v-moura.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/41/Remy_charg-o-matic_car_battery.jpg",
    ),
    "Kit distribucion Renault": (
        "kit-distribucion-renault.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/6/62/Zahnriemen_Suzuki_G10A.JPG",
    ),
    "Amortiguador delantero Corven": (
        "amortiguador-delantero-corven.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Buggy_shock_tower.jpg",
    ),
    "Bujias NGK x4": (
        "bujias-ngk-x4.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/7c/Spark_plug_2.jpg",
    ),
    "Liquido refrigerante 5L": (
        "liquido-refrigerante-5l.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/79/Engine_coolant.jpg",
    ),
    "Radiador Peugeot 206": (
        "radiador-peugeot-206.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/3/37/Honeycomb_radiator_tubes.jpg",
    ),
    "Optica derecha Gol Trend": (
        "optica-derecha-gol-trend.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/5b/Headlight_of_a_Soviet_car.jpg",
    ),
    "Sensor MAP Fiat": (
        "sensor-map-fiat.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/0/09/Manifoldpresser.JPG",
    ),
    "Embrague completo Corsa": (
        "embrague-completo-corsa.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/5b/Clutchdisc.jpg",
    ),
    "SSD Kingston 480GB": (
        "ssd-kingston-480gb.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/a3/Crucial_CT256M4SSD2_rear_20120123.jpg",
    ),
    "Memoria DDR4 8GB": (
        "memoria-ddr4-8gb.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/6/6c/RAM_Module_%28SDRAM-DDR4%29.jpg",
    ),
    "Fuente ATX 600W": (
        "fuente-atx-600w.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/af/ATX_Computer_power_supply_unit.jpg",
    ),
    "Pasta termica Arctic": (
        "pasta-termica-arctic.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/W%C3%A4rmeleitpaste_Thermal_Compound.jpg",
    ),
    "Cargador notebook universal": (
        "cargador-notebook-universal.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/79/Lenovo_65W_20V_AC_adapter_%28FRU_42T5283%29_for_ThinkPad_laptops.jpg",
    ),
    "Pantalla notebook 15.6": (
        "pantalla-notebook-156.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/c/c9/Disassembled_LCD_screen_assembly_of_a_Lenovo_ThinkPad_X220.jpg",
    ),
    "Teclado notebook Lenovo": (
        "teclado-notebook-lenovo.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/13/Laptop_Keyboard_1.jpg",
    ),
    "Cooler CPU universal": (
        "cooler-cpu-universal.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/be/Asus_P5PL2_-_CPU_heatsink_with_cooling_fan-5293.jpg",
    ),
}


PEDIDOS_DEMO = [
    ("tecnico_prueba", "repuestos_rawson", "Kit distribucion Renault", 1, "retiro", "completado", 9, 6),
    ("tecnico_prueba", "repuestos_rawson", "Bujias NGK x4", 2, "envio", "completado", 7, 7),
    ("tecnico_rawson", "autopartes_chubut", "Radiador Peugeot 206", 1, "retiro", "completado", 6, 4),
    ("tecnico_rawson", "autopartes_chubut", "Optica derecha Gol Trend", 1, "envio", "aceptado", 3, 2),
    ("tecnico_prueba", "proveedor_prueba", "Pastillas de freno Bosch", 1, "retiro", "completado", 5, 5),
    ("tecnico_rawson", "tecno_rawson", "SSD Kingston 480GB", 2, "retiro", "completado", 8, 3),
    ("tecnico_rawson", "tecno_rawson", "Pasta termica Arctic", 3, "envio", "completado", 4, 4),
    ("tecnico_prueba", "electronica_puerto", "Pantalla notebook 15.6", 1, "envio", "completado", 2, 1),
    ("tecnico_rawson", "electronica_puerto", "Cargador notebook universal", 1, "retiro", "pendiente", 1, 0),
]


class Command(BaseCommand):
    help = "Crea usuarios, proveedores, productos y pedidos de prueba"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los usuarios demo existentes antes de crearlos",
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

        productos_creados = self.crear_productos_demo()
        pedidos_creados = self.crear_pedidos_demo()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de prueba listos:"))
        self.stdout.write("  admin / admin1234")
        self.stdout.write("  tecnico_prueba / tecnico1234")
        self.stdout.write("  tecnico_rawson / tecnico1234")
        self.stdout.write("  proveedores demo / proveedor1234")
        self.stdout.write(f"  {productos_creados} productos demo creados")
        self.stdout.write(f"  {pedidos_creados} pedidos demo creados")

    def crear_productos_demo(self):
        creados = 0
        for username, productos in PRODUCTOS_DEMO.items():
            try:
                proveedor = User.objects.get(username=username).proveedor
            except (User.DoesNotExist, Proveedor.DoesNotExist):
                continue

            for nombre, descripcion, modelo, categoria, precio, stock in productos:
                imagen = self.obtener_imagen_producto(nombre)
                producto, creado = Producto.objects.get_or_create(
                    proveedor=proveedor,
                    nombre=nombre,
                    defaults={
                        "descripcion": descripcion,
                        "imagen": imagen,
                        "modelo": modelo,
                        "categoria": categoria,
                        "precio": Decimal(precio),
                        "stock": stock,
                        "disponible": True,
                    },
                )
                if imagen and producto.imagen.name != imagen:
                    producto.imagen = imagen
                    producto.save(update_fields=["imagen"])
                if creado:
                    creados += 1
        return creados

    def obtener_imagen_producto(self, nombre):
        datos_imagen = PRODUCTOS_DEMO_IMAGENES.get(nombre)
        if not datos_imagen:
            return ""

        archivo, url = datos_imagen
        ruta = Path(settings.MEDIA_ROOT) / "productos" / archivo
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if not ruta.exists():
            if not self.descargar_imagen_producto(nombre, url, ruta):
                return ""
        return f"productos/{archivo}"

    def descargar_imagen_producto(self, nombre, url, ruta):
        for url_descarga in self.urls_descarga_imagen(url):
            sleep(1)
            request = Request(url_descarga, headers={"User-Agent": "gestion-repuestos-demo/1.0"})
            try:
                with urlopen(request, timeout=20) as response:
                    ruta.write_bytes(response.read())
                return True
            except (OSError, URLError) as exc:
                ultimo_error = exc

        self.stdout.write(self.style.WARNING(f"  No se pudo descargar imagen de '{nombre}': {ultimo_error}"))
        return False

    def urls_descarga_imagen(self, url):
        parsed = urlparse(url)
        partes = parsed.path.split("/")
        if parsed.netloc == "upload.wikimedia.org" and "/wikipedia/commons/" in parsed.path and "/thumb/" not in parsed.path:
            archivo = partes[-1]
            base = "/".join(partes[:-1]).replace("/wikipedia/commons/", "/wikipedia/commons/thumb/", 1)
            yield f"{parsed.scheme}://{parsed.netloc}{base}/{archivo}/800px-{archivo}"
        yield url

    def crear_pedidos_demo(self):
        creados = 0
        ahora = timezone.now()
        for tecnico_username, proveedor_username, producto_nombre, cantidad, entrega, estado, dias_atras, horas_respuesta in PEDIDOS_DEMO:
            try:
                tecnico = User.objects.get(username=tecnico_username).tecnico
                proveedor = User.objects.get(username=proveedor_username).proveedor
                producto = Producto.objects.get(proveedor=proveedor, nombre=producto_nombre)
            except (User.DoesNotExist, Tecnico.DoesNotExist, Proveedor.DoesNotExist, Producto.DoesNotExist):
                continue

            marcador = f"pedido demo {tecnico_username}-{proveedor_username}-{producto_nombre}"
            if Pedido.objects.filter(tecnico=tecnico, proveedor=proveedor, producto=producto, notas=marcador).exists():
                continue

            pedido = Pedido.objects.create(
                tecnico=tecnico,
                proveedor=proveedor,
                producto=producto,
                cantidad=cantidad,
                forma_entrega=entrega,
                estado=estado,
                monto_total=producto.precio * Decimal(cantidad),
                notas=marcador,
                respuesta_proveedor="Confirmado para demo." if estado != "pendiente" else None,
            )
            fecha_creacion = ahora - timedelta(days=dias_atras)
            fecha_actualizacion = fecha_creacion + timedelta(hours=horas_respuesta)
            if estado == "pendiente":
                fecha_actualizacion = fecha_creacion
            Pedido.objects.filter(pk=pedido.pk).update(
                fecha_creacion=fecha_creacion,
                fecha_actualizacion=fecha_actualizacion,
            )
            creados += 1
        return creados
