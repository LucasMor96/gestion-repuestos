# Gestion Repuestos

Aplicacion web desarrollada con Django para gestionar la compra y venta de repuestos entre tecnicos independientes y proveedores.

El sistema permite registrar tecnicos y proveedores, moderar altas de usuarios, publicar catalogos de productos, buscar repuestos, generar pedidos, administrar credito comercial y calificar operaciones completadas.

## Caracteristicas

- Registro diferenciado de tecnicos y proveedores.
- Flujo de aprobacion, rechazo, suspension y solicitud de informacion para usuarios.
- Login por email.
- Dashboard segun tipo de usuario.
- Catalogo de productos para proveedores.
- Busqueda de repuestos por nombre, modelo, categoria, precio y distancia.
- Creacion, aceptacion, rechazo, cancelacion y finalizacion de pedidos.
- Exportacion del historial de pedidos a CSV.
- Gestion de credito entre proveedores y tecnicos.
- Alertas de nuevos pedidos, cambios de estado y uso de credito.
- Calificaciones de proveedores y tecnicos sobre pedidos completados.
- Panel de administracion de Django.

## Stack

- Python
- Django 5.2.13
- PostgreSQL
- HTML templates de Django

## Estructura principal

```text
gestion-repuestos/
|-- config/                 # Configuracion y composicion global de URLs
|-- apps/                   # Aplicaciones Django del dominio
|   |-- core/               # Inicio, dashboard, 404 y recursos compartidos
|   |-- usuarios/           # Tecnicos, proveedores, autenticacion y moderacion
|   |-- catalogo/           # Productos, busqueda y catalogo del proveedor
|   |-- pedidos/            # Flujo de pedidos y sus notificaciones
|   |-- creditos/           # Credito comercial, deuda y notificaciones
|   `-- calificaciones/     # Calificaciones posteriores a una operacion
|-- media/                  # Archivos subidos por usuarios
|-- manage.py
|-- requeriments.txt
`-- .env.example
```

Cada app dentro de `apps/` contiene sus propios modelos, formularios, vistas, URLs, templates,
administracion, migraciones y pruebas cuando corresponda. Las URLs publicas se
componen sin namespaces para conservar sus nombres historicos.

Para una guia de onboarding con el mapa interno de archivos, vistas, modelos y flujos de negocio, ver [`docs/guia_desarrollador.md`](docs/guia_desarrollador.md).

## Requisitos

- Python 3.11 o superior recomendado.
- PostgreSQL instalado y corriendo.
- Una base de datos PostgreSQL creada para el proyecto.

> Nota: el archivo de dependencias se llama `requeriments.txt`. El proyecto usa `python-dotenv` desde `config/settings.py`; si tu entorno nuevo no lo tiene instalado, instalalo junto con las dependencias.

## Instalacion

1. Crear y activar un entorno virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

En Linux/macOS:

```bash
python -m venv venv
source venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requeriments.txt python-dotenv Pillow
```

3. Crear el archivo de variables de entorno:

```bash
copy .env.example .env
```

En Linux/macOS:

```bash
cp .env.example .env
```

4. Editar `.env` con los datos de PostgreSQL:

```env
DB_NAME=gestion_repuestos
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
DB_HOST=localhost
DB_PORT=5432
```

La recuperación de contraseña se gestiona sin email: el administrador puede restablecerla desde el panel de Django. Los usuarios autenticados pueden cambiarla desde “Cambiar contraseña”.

5. Crear la base de datos en PostgreSQL si todavia no existe:

```sql
CREATE DATABASE gestion_repuestos;
```

6. Aplicar migraciones sobre una base vacia:

```bash
python manage.py migrate
```

La historia de migraciones comienza con las seis apps actuales. Si se detectan
tablas de la antigua app `plataforma`, una migracion de `core` importa sus datos
a las tablas nuevas conservando IDs y relaciones.

7. Crear usuarios de prueba:

```bash
python manage.py crear_usuarios_prueba
```

Para recrearlos desde cero:

```bash
python manage.py crear_usuarios_prueba --reset
```

8. Levantar el servidor:

```bash
python manage.py runserver
```

La aplicacion queda disponible en:

```text
http://127.0.0.1:8000/
```

## Usuarios de prueba

El comando `crear_usuarios_prueba` genera estos accesos:

| Rol | Usuario | Email | Password |
| --- | --- | --- | --- |
| Admin | `admin` | `admin@repuestos.com` | `admin1234` |
| Tecnico | `tecnico_prueba` | `tecnico@repuestos.com` | `tecnico1234` |
| Proveedor | `proveedor_prueba` | `proveedor@repuestos.com` | `proveedor1234` |

El login de la aplicacion se realiza con email y password.

## Rutas utiles

| Ruta | Descripcion |
| --- | --- |
| `/` | Inicio |
| `/registro/` | Seleccion de tipo de registro |
| `/registro/tecnico/` | Registro de tecnico |
| `/registro/proveedor/` | Registro de proveedor |
| `/login/` | Inicio de sesion |
| `/password-reset/` | Recuperacion de contrasena |
| `/dashboard/` | Panel principal |
| `/buscar/` | Busqueda de repuestos |
| `/catalogo/` | Catalogo del proveedor |
| `/pedidos/` | Pedidos del tecnico |
| `/pedidos/recibidos/` | Pedidos recibidos por proveedor |
| `/credito/` | Creditos del tecnico |
| `/credito/gestionar/` | Gestion de creditos del proveedor |
| `/moderacion/` | Moderacion de usuarios, solo staff |
| `/admin/` | Administracion de Django |

## Flujo basico de uso

1. Un tecnico o proveedor se registra.
2. El usuario queda pendiente de aprobacion.
3. Un usuario staff aprueba, rechaza, suspende o solicita informacion desde moderacion.
4. El proveedor carga productos en su catalogo.
5. El tecnico busca repuestos y crea pedidos.
6. El proveedor acepta, rechaza o propone una alternativa.
7. El tecnico puede marcar el pedido aceptado como completado.
8. Luego ambas partes pueden calificarse.

Cuando el administrador pide informacion, la cuenta permanece pendiente. Al ingresar
con su email y contrasena, el usuario puede leer la solicitud y responder con texto
o hasta cinco imagenes JPG, PNG o WebP (5 MB por imagen). Este acceso solo permite
consultar la revision durante una hora; no habilita las funciones de una cuenta aprobada.
El panel de moderacion conserva las respuestas y permite ampliar las imagenes.
Los adjuntos se guardan en `private_media/`, fuera del directorio publico `media/`,
y se entregan unicamente al propietario o al staff. Incluir este directorio en los
respaldos y no publicarlo directamente desde el servidor web.

## Conservacion del historial y habilitacion de proveedores

Los productos con pedidos asociados no se pueden eliminar, tampoco desde el
administrador ni mediante borrado masivo del ORM. Se pueden ocultar del catalogo
para impedir nuevas compras, conservando pedidos, comprobantes, calificaciones y
credito. Los productos sin pedidos se pueden eliminar normalmente.

El catalogo y sus categorias solo muestran productos visibles de proveedores con
estado aprobado, aprobacion vigente y usuario activo. La creacion de pedidos
vuelve a verificar esos datos bajo bloqueo transaccional para impedir compras
con formularios abiertos antes de una suspension.

## Comandos frecuentes

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py crear_usuarios_prueba
python manage.py runserver
```
