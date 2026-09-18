# Guia para desarrolladores

Gestion Repuestos es un monolito Django dividido en apps por responsabilidad. El
proyecto global se llama `config`; no existe una app central con todos los modelos.

## Arquitectura

| App | Responsabilidad | Dependencias de dominio |
| --- | --- | --- |
| `usuarios` | Tecnicos, proveedores, registro, login, perfiles y moderacion | Django auth |
| `catalogo` | Productos, busqueda y gestion del catalogo | `usuarios` |
| `creditos` | Limites, saldos y deudas | `usuarios`; consulta pedidos desde sus vistas |
| `pedidos` | Solicitudes, estados, pagos y exportacion | `usuarios`, `catalogo`, `creditos` |
| `calificaciones` | Opiniones de tecnicos y proveedores | `usuarios`, `pedidos` |
| `core` | Inicio, dashboard, 404, layout, assets y datos de demostracion | Compone las apps de dominio |

Cada app expone sus rutas desde `urls.py`. `config/urls.py` incluye todos esos
modulos sin namespace, por lo que nombres como `crear_pedido`, `mis_creditos` y
`dashboard` se mantienen estables.

## Capas dentro de cada app

Las views son adaptadores HTTP: comprueban acceso, instancian formularios,
invocan un caso de uso y traducen el resultado a mensajes, redirects o un
template. No contienen transiciones de estado ni coordinan escrituras sobre
varios modelos.

- `forms.py`: valida y normaliza datos provenientes del usuario.
- `services.py`: ejecuta casos de uso y reglas de negocio. Recibe modelos o
  valores explicitos, nunca `request`; las operaciones de varias escrituras son
  atomicas y exponen excepciones de dominio esperadas.
- `selectors.py` y QuerySets: encapsulan consultas, filtros y anotaciones
  reutilizables sin producir efectos secundarios.
- `models.py`: conserva propiedades e invariantes propias de una sola entidad.

Los CRUD triviales pueden permanecer coordinados por una view. En cuanto una
accion modifica mas de una entidad, cambia estados, ajusta stock o saldo, o se
reutiliza desde otro flujo, debe convertirse en un servicio.

## Donde buscar cada cambio

El recorrido habitual de una funcionalidad es `urls.py` -> `views.py` ->
`forms.py` -> `services.py`/`selectors.py` -> `models.py` ->
`templates/<app>/`. Cada modelo se registra en el
`admin.py` de su propia app y posee una migracion inicial local.

- Autenticacion, perfiles, aprobacion y permisos: `apps/usuarios/`.
- Productos, filtros y busqueda: `apps/catalogo/`.
- Ciclo de compra, comprobantes y exportacion: `apps/pedidos/`.
- Limites y deuda comercial: `apps/creditos/`.
- Calificaciones posteriores a pedidos completados: `apps/calificaciones/`.
- Paginas que componen varios dominios: `apps/core/`.

Los helpers de rol y aprobacion viven en `apps/usuarios/utils.py`.
El contador global de pedidos pendientes se configura desde
`apps/pedidos/context_processors.py`.

## Registro, autenticacion y sesiones

- Los formularios de registro heredan de `UserCreationForm`. Su `save()` es
  atomico: crea el `User` inactivo y su perfil pendiente en la misma transaccion.
  Si falla el perfil, tampoco queda creada la cuenta. Las vistas convierten los
  conflictos de email o CUIT posteriores a la validacion en errores de formulario.
- Los emails se guardan sin espacios externos y en minusculas. Registro y login
  usan la misma normalizacion; `usuarios_por_email()` tambien contempla emails
  historicos con otra capitalizacion o espacios. El registro limita el email a
  la longitud de `username`, porque usa ese valor como nombre de usuario.
- `usuarios.0003_email_unico_normalizado` normaliza los emails existentes y agrega
  un indice unico funcional sobre `auth_user`, administrado por esta migracion.
  No cambia el modelo de Django, usernames, IDs, claves ni relaciones. Permite
  varias cuentas sin email. Si encuentra emails equivalentes, detiene la
  migracion sin modificar ni eliminar cuentas: se deben corregir antes de reintentar.
  Al revertirla se quita el indice; la normalizacion de emails se conserva.
- El login comercial exige `is_active`, `estado='aprobado'` e `is_approved`.
  El staff activo puede ingresar sin perfil comercial. Las cuentas no habilitadas
  con credenciales validas solo reciben acceso firmado de moderacion por una hora.
- Los templates de registro conservan los datos de entrada ante errores, salvo
  las contrasenas, cuyos campos siempre quedan vacios.
- `/logout/` solo acepta POST. El boton de la plantilla base envia el token CSRF;
  un GET no cierra la sesion. El cierre tambien elimina el acceso de moderacion.

## Edicion y paginacion del catalogo

La edicion de productos, tanto del proveedor como del admin, incluye una huella
firmada del estado que se mostro al abrir el formulario. En POST se bloquea la
fila del producto antes de validar y guardar. Si cambio stock, precio u otro
campo, se rechaza el formulario antiguo y se pide recargar; no se sobrescribe el
descuento de una compra. Los formularios abiertos antes de incorporar esta
proteccion tambien deben recargarse. No requiere cambios de esquema.

`apps/catalogo/paginacion.py` define 24 productos por pagina para la busqueda
publica, la busqueda del tecnico y el catalogo propio del proveedor. Los enlaces
conservan los filtros y el orden usa el ID para desempatar. La busqueda evalua
solo la pagina solicitada dentro del manejo de errores de base de datos.

Para tecnicos, `ProductoQuerySet.con_calificacion_proveedor()` anota el promedio
con una subconsulta; el template no consulta la propiedad del proveedor por cada
tarjeta. Las unidades vendidas se calculan solo al ordenar por mas vendidos,
sin unir calificaciones y pedidos de una manera que multiplique los totales.

Las regresiones de edicion, bloqueo simultaneo, paginacion y cantidad de
consultas se cubren en `apps/catalogo/test_edicion_paginacion.py`.

## Templates, static y media

Los templates usan el namespace de su app, por ejemplo
`pedidos/crear_pedido.html`, y extienden `core/base.html`. Los mapas, logos y
otros assets compartidos viven en `apps/core/static/core/`. `media/` conserva las
imagenes, logos, comprobantes y demas archivos cargados por usuarios.

## Modelos y relaciones

- `usuarios.Tecnico` y `usuarios.Proveedor` extienden a `User` mediante relaciones uno a uno.
- `catalogo.Producto` pertenece a un proveedor.
- `pedidos.Pedido` conecta tecnico, proveedor y producto.
- `creditos.Credito` define un limite unico por proveedor y tecnico.
- Las calificaciones conectan un pedido completado con ambas partes.

Las dependencias entre migraciones siguen esas relaciones. La historia actual
parte de migraciones `0001_initial`. `core.0001_import_legacy_data` detecta una
base migrada con la antigua app `plataforma` y copia sus registros a las nuevas
tablas en orden de dependencias; sobre una base vacia es una operacion nula.

## Desarrollo y verificacion

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
python manage.py crear_usuarios_prueba
python manage.py runserver
```

Las pruebas se distribuyen por app. `apps/core/tests.py` contiene escenarios de
integracion transversal y 404; `apps/usuarios/tests.py` cubre acceso y perfiles;
`apps/pedidos/tests.py` cubre el ciclo de pedido y sus notificaciones.

El comando `crear_usuarios_prueba`, ubicado en `apps/core/management/commands/`, crea
los tres roles de demostracion y datos relacionados de varias apps. La opcion
`--reset` elimina y vuelve a generar solo esos datos de prueba.

## Checklist para nuevas funcionalidades

1. Elegir la app propietaria por responsabilidad, no por la pantalla desde la que se accede.
2. Modificar modelo y migracion dentro de esa app si cambia la persistencia.
3. Mantener formulario, vista, template, admin y pruebas junto al dominio.
4. Importar modelos desde su app propietaria y evitar fachadas globales.
5. Agregar la ruta al `urls.py` local; conservar nombres publicos existentes.
6. Ejecutar checks, migraciones pendientes y toda la suite antes de entregar.
