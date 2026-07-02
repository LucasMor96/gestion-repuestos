# Guia para desarrolladores

Esta guia explica donde esta cada parte importante del proyecto y por donde conviene empezar cuando alguien nuevo se suma al desarrollo.

El proyecto es una aplicacion Django para gestionar pedidos de repuestos entre tecnicos independientes y proveedores. La app principal se llama `plataforma`; el proyecto Django global se llama `config`.

## Mapa rapido

```text
gestion-repuestos/
|-- config/                         Configuracion global de Django
|   |-- settings.py                  Apps instaladas, base de datos, templates, media, email
|   |-- urls.py                      URLs globales: admin, app principal y 404
|   |-- asgi.py / wsgi.py            Entrada ASGI/WSGI
|
|-- plataforma/                      App principal del negocio
|   |-- models/                      Modelos separados por dominio
|   |-- views/                       Vistas separadas por funcionalidad
|   |-- templates/plataforma/        Pantallas HTML de la app
|   |-- static/plataforma/           Assets estaticos propios
|   |-- migrations/                  Migraciones de base de datos
|   |-- management/commands/         Comandos custom de Django
|   |-- admin.py                     Configuracion del admin
|   |-- forms.py                     Formularios de registro, pedidos, catalogo, credito, etc.
|   |-- urls.py                      Rutas de la app principal
|   |-- context_processors.py        Datos globales para templates
|   |-- password_validators.py       Validador custom de passwords
|
|-- media/                           Archivos subidos o generados localmente
|-- docs/                            Documentacion interna
|-- manage.py                        CLI de Django
|-- requeriments.txt                 Dependencias Python
|-- README.md                        Instalacion, comandos y flujo general
|-- .env.example                     Variables de entorno esperadas
```

## Por donde entrar

Para entender una pantalla o flujo, el recorrido normal es:

1. Buscar la ruta en `plataforma/urls.py`.
2. Ver que funcion de vista se llama.
3. Abrir el modulo real dentro de `plataforma/views/`.
4. Ver que formulario usa en `plataforma/forms.py`.
5. Ver que modelos consulta o modifica en `plataforma/models/`.
6. Abrir el template renderizado en `plataforma/templates/plataforma/`.

Ejemplo: la ruta `pedidos/crear/<int:producto_pk>/` apunta a `crear_pedido`, que esta exportada desde `plataforma/views/__init__.py`, pero la logica real esta en `plataforma/views/pedidos.py`. Esa vista usa `PedidoForm` de `forms.py`, escribe un `Pedido` y renderiza `templates/plataforma/crear_pedido.html`.

## Proyecto Django global

### `config/settings.py`

Define la configuracion general:

- `INSTALLED_APPS` incluye la app `plataforma`.
- La base de datos esta configurada para PostgreSQL y lee valores desde `.env`.
- `TEMPLATES` usa `APP_DIRS=True`, por eso Django encuentra templates dentro de `plataforma/templates/`.
- `plataforma.context_processors.pedidos_pendientes` inyecta el contador de pedidos pendientes en todos los templates.
- `MEDIA_URL` y `MEDIA_ROOT` sirven archivos subidos en desarrollo.
- `EMAIL_BACKEND` y `DEFAULT_FROM_EMAIL` salen del entorno, con backend de consola por defecto.

### `config/urls.py`

Centraliza las rutas globales:

- `/admin/` va al admin de Django.
- `/` delega todo lo de negocio a `plataforma.urls`.
- Agrega `static(settings.MEDIA_URL, ...)` para servir archivos de `media/` en desarrollo.
- Define `not_found` como handler 404 y fallback para rutas desconocidas.

## App principal: `plataforma`

### `plataforma/urls.py`

Es el indice de navegacion de la aplicacion. Agrupa rutas de:

- Autenticacion y registro.
- Dashboard y perfiles.
- Busqueda de repuestos.
- Catalogo de proveedores.
- Pedidos.
- Calificaciones.
- Credito comercial.
- Moderacion.
- Recuperacion de password con vistas genericas de Django.

Si queres agregar una pantalla nueva, normalmente agregas aca el `path`, luego creas o reutilizas una vista y su template.

### `plataforma/views/__init__.py`

Funciona como fachada. Importa funciones desde archivos como `auth.py`, `pedidos.py` y `creditos.py`, y las expone para que `plataforma/urls.py` pueda hacer `from . import views`.

Importante: si agregas una vista nueva en un modulo, y queres referenciarla como `views.mi_vista`, tambien tenes que exportarla en este archivo.

### `plataforma/forms.py`

Contiene la mayoria de validaciones de entrada del usuario:

- `RegistroTecnicoForm` y `RegistroProveedorForm`: crean el `User` y el perfil asociado.
- `LoginForm`: login por email.
- `EditarPerfilTecnicoForm` y `EditarPerfilProveedorForm`: edicion de perfiles.
- `ProductoForm`: alta y edicion de catalogo.
- `PedidoForm`: solicitud de repuestos, entrega, forma de pago y comprobante.
- `GestionarPedidoForm`: decision del proveedor sobre un pedido.
- `AsignarCreditoForm`: limite de credito.
- `CalificacionProveedorForm` y `CalificacionTecnicoForm`: calificaciones post pedido.

Cuando el cambio sea una regla de negocio sobre datos ingresados por el usuario, primero revisar este archivo.

### `plataforma/admin.py`

Registra los modelos en el admin de Django y define columnas, filtros, buscadores y campos de solo lectura. Es util para debugging y carga manual de datos.

### `plataforma/context_processors.py`

Tiene `pedidos_pendientes(request)`, que agrega `pedidos_pendientes_count` al contexto global de templates para proveedores autenticados.

### `plataforma/views/utils.py`

Helpers compartidos por varias vistas:

- `solo_staff(request)`: valida acceso staff para moderacion.
- `perfil_aprobado(perfil)`: verifica usuario activo, estado aprobado e `is_approved`.
- `get_proveedor_o_403(request)`: obtiene el proveedor del usuario o devuelve `None` y mensaje.
- `get_tecnico_o_403(request)`: obtiene el tecnico del usuario o devuelve `None` y mensaje.
- `haversine(...)`: calcula distancia en km entre coordenadas.

Antes de repetir validaciones de rol o aprobacion, revisar este archivo.

### `plataforma/views/notifications.py`

Centraliza emails transaccionales. Usa `django.core.mail.send_mail` y el backend configurado en `settings.py`.

Notificaciones actuales:

- Nuevo pedido para proveedor.
- Cambio de estado de pedido para tecnico.
- Pedido completado.
- Credito asignado.
- Alerta por uso de credito.
- Deuda saldada.
- Credito revocado.

En desarrollo, con el backend de consola, los emails se imprimen en la terminal.

## Modelos

Los modelos estan separados en archivos chicos y se reexportan desde `plataforma/models/__init__.py`.

| Archivo | Modelo / contenido | Responsabilidad |
| --- | --- | --- |
| `models/choices.py` | Choices compartidos | Rubros, estados de usuario y estrellas |
| `models/tecnico.py` | `Tecnico` | Perfil del tecnico, ubicacion, estado de aprobacion, promedio recibido |
| `models/proveedor.py` | `Proveedor` | Perfil del proveedor, datos comerciales, medios de transferencia, imagenes, promedio recibido |
| `models/producto.py` | `Producto` | Catalogo del proveedor, precio, stock, disponibilidad e imagen |
| `models/pedido.py` | `Pedido` | Pedido entre tecnico y proveedor, entrega, pago, estado, monto, comprobante |
| `models/credito.py` | `Credito` | Limite, saldo usado y saldo disponible entre proveedor y tecnico |
| `models/calificaciones.py` | `CalificacionProveedor`, `CalificacionTecnico` | Opiniones despues de pedidos completados |

Relaciones clave:

- `Tecnico.usuario` y `Proveedor.usuario` son `OneToOneField` a `django.contrib.auth.models.User`.
- `Producto.proveedor` pertenece a un proveedor.
- `Pedido` conecta `Tecnico`, `Proveedor` y `Producto`.
- `Credito` conecta proveedor y tecnico, con `unique_together`.
- Las calificaciones pertenecen a un pedido y solo se guardan si el pedido esta `completado`.

## Vistas por funcionalidad

| Modulo | Que maneja | Templates principales |
| --- | --- | --- |
| `views/auth.py` | Inicio, registro, login/logout, dashboard, espera de aprobacion, edicion y visualizacion de perfiles | `inicio.html`, `registro_*.html`, `login.html`, `dashboard.html`, `espera_aprobacion.html`, `editar_perfil.html`, `perfil_tecnico.html`, `perfil_proveedor.html` |
| `views/search.py` | Busqueda de productos por texto, categoria, precio/distancia/ventas | `buscar_repuestos.html` |
| `views/catalogo.py` | Catalogo del proveedor: listar, agregar, editar, eliminar, activar/desactivar | `catalogo_proveedor.html`, `producto_form.html` |
| `views/pedidos.py` | Crear pedidos, listar propios, exportar CSV, cancelar, recibir, gestionar y completar | `crear_pedido.html`, `mis_pedidos.html`, `pedidos_recibidos.html`, `detalle_pedido_proveedor.html` |
| `views/creditos.py` | Creditos del tecnico, gestion del proveedor, asignacion, revocacion, deudas y saldos | `mis_creditos.html`, `gestionar_creditos_proveedor.html`, `asignar_credito.html`, `deudas_tecnicos.html`, `detalle_deuda_tecnico.html` |
| `views/calificaciones.py` | Calificar proveedor o tecnico luego de completar pedidos | `calificar_proveedor.html`, `calificar_tecnico.html` |
| `views/moderacion.py` | Panel staff para aprobar, rechazar, suspender o pedir informacion | `panel_moderacion.html` |
| `views/errors.py` | Pagina 404 | `404.html` |
| `views/notifications.py` | Envio de emails transaccionales | No renderiza templates |
| `views/utils.py` | Helpers de permisos, perfiles y distancia | No renderiza templates |

## Templates y UI

Los templates viven en `plataforma/templates/plataforma/`.

- `base.html` es el layout compartido: navbar, mensajes, bloques comunes y carga de estilos/scripts.
- Las pantallas de negocio extienden `base.html`.
- `includes/static_location_map.html` es un parcial reutilizable para mostrar ubicaciones.
- Los templates de password reset usan las vistas genericas de Django configuradas en `plataforma/urls.py`.
- `404.html` esta en `plataforma/templates/404.html`, fuera de la subcarpeta `plataforma`, porque la vista lo renderiza como `'404.html'`.

Si el cambio es visual, casi siempre empieza en un template. Si tambien cambia informacion mostrada, revisar la vista que arma el contexto.

## Static y media

### Static

Archivos versionados de la app:

- `plataforma/static/plataforma/js/address-map.js`: inicializa mapas/ubicaciones desde atributos `data-*`.
- `plataforma/static/plataforma/img/luma-logo.svg` y `luma-mark.svg`: marca visual.

### Media

`media/` guarda archivos generados o subidos localmente:

- Imagenes de productos.
- Logos e imagenes de proveedores.
- Comprobantes de transferencia.

No conviene depender de contenido local de `media/` para logica de negocio. Es un directorio de archivos cargados, no codigo fuente.

## Flujos importantes

### Registro y aprobacion

1. El usuario elige tipo en `registro_tipo`.
2. `RegistroTecnicoForm` o `RegistroProveedorForm` crea un `User` inactivo y su perfil.
3. El usuario queda en espera.
4. Un staff entra a moderacion.
5. `aprobar_usuario`, `rechazar_usuario`, `suspender_usuario` o `solicitar_info` actualizan `estado`, `is_approved` y `User.is_active`.
6. Las vistas protegidas usan helpers de `views/utils.py` para validar que el perfil este aprobado.

### Catalogo

1. El proveedor aprobado entra a `/catalogo/`.
2. `catalogo_proveedor` lista sus productos.
3. `ProductoForm` valida altas y ediciones.
4. `toggle_disponibilidad` oculta o muestra productos sin borrarlos.
5. La busqueda solo deberia mostrar productos disponibles y con proveedor habilitado.

### Pedido

1. El tecnico busca en `/buscar/`.
2. Desde un producto va a `crear_pedido`.
3. `PedidoForm` valida cantidad, entrega, pago y comprobante.
4. Se crea un `Pedido`, se calcula `monto_total` y se notifica al proveedor.
5. El proveedor ve el pedido en `/pedidos/recibidos/`.
6. Desde el detalle lo acepta, rechaza o propone alternativa con `GestionarPedidoForm`.
7. El tecnico puede completar pedidos aceptados.
8. Al completar, se habilitan calificaciones.

### Credito comercial

1. El proveedor asigna credito desde `/credito/asignar/`.
2. `Credito` guarda limite y saldo usado para un par proveedor/tecnico.
3. El tecnico puede usar `credito_comercial` como forma de pago si tiene saldo disponible.
4. Los pedidos con credito actualizan `saldo_usado`.
5. El proveedor puede revisar deudas, marcar saldo como pagado o revocar credito.

### Calificaciones

1. Solo se califican pedidos `completado`.
2. El tecnico califica al proveedor con `CalificacionProveedor`.
3. El proveedor califica al tecnico con `CalificacionTecnico`.
4. Los modelos impiden guardar calificaciones si el pedido no esta completado.
5. Los promedios se exponen como propiedades en `Tecnico` y `Proveedor`.

## Datos de prueba

El comando custom esta en:

```text
plataforma/management/commands/crear_usuarios_prueba.py
```

Uso:

```bash
python manage.py crear_usuarios_prueba
python manage.py crear_usuarios_prueba --reset
```

Genera usuarios, perfiles, proveedores, productos demo e historial de pedidos. Tambien intenta descargar imagenes de productos en `media/productos/`.

## Comandos utiles

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py crear_usuarios_prueba
python manage.py createsuperuser
python manage.py runserver
```

Para buscar rapido en el codigo:

```bash
rg "crear_pedido"
rg "PedidoForm"
rg "render\\("
rg "path\\("
```

## Como agregar una funcionalidad

Checklist recomendado:

1. Definir si necesita nuevo modelo o campo.
2. Agregar/editar modelo en `plataforma/models/`.
3. Exportarlo en `plataforma/models/__init__.py` si es un modelo nuevo.
4. Crear migracion con `python manage.py makemigrations`.
5. Agregar o modificar formulario en `plataforma/forms.py`.
6. Agregar vista en el modulo correcto de `plataforma/views/`.
7. Exportar la vista en `plataforma/views/__init__.py` si la URL la va a usar como `views.nombre`.
8. Agregar ruta en `plataforma/urls.py`.
9. Crear o editar template en `plataforma/templates/plataforma/`.
10. Registrar cambios en `admin.py` si conviene verlo desde Django admin.
11. Ejecutar `python manage.py check` y probar el flujo manualmente.

## Convenciones del proyecto

- Las rutas usan nombres de URL en castellano: `mis_pedidos`, `catalogo_proveedor`, `panel_moderacion`.
- Las vistas son funciones, no class-based views, excepto las genericas de password reset.
- Los permisos se resuelven en vistas con `@login_required`, `@require_POST` y helpers de `views/utils.py`.
- La app usa el sistema de mensajes de Django para feedback al usuario.
- Los templates usan Bootstrap por clases.
- El login se hace con email, pero internamente Django sigue usando `User.username`; en registro se setea `username = email`.
- Los estados importantes se guardan como strings con choices en los modelos.

## Lugares a revisar ante problemas comunes

| Problema | Donde mirar |
| --- | --- |
| No entra un tecnico/proveedor a una vista | `views/utils.py`, estado del perfil, `User.is_active` |
| Una ruta da 404 | `plataforma/urls.py`, `config/urls.py`, nombre de URL en template |
| Un template no encuentra una variable | Vista correspondiente y contexto enviado al `render` |
| No aparece un producto en busqueda | `views/search.py`, `Producto.disponible`, stock, proveedor aprobado |
| No se puede crear pedido | `PedidoForm`, stock del producto, forma de pago, credito disponible |
| No se envia mail | `.env`, `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`, `views/notifications.py` |
| Imagen no carga | Campo `ImageField`, archivo en `media/`, `MEDIA_URL` y `config/urls.py` |
| Falla una migracion | Modelo modificado, archivos en `plataforma/migrations/`, base local |

