# Guia para desarrolladores

Gestion Repuestos es un monolito Django dividido en apps por responsabilidad. El
proyecto global se llama `config`; no existe una app central con todos los modelos.

## Arquitectura

| App | Responsabilidad | Dependencias de dominio |
| --- | --- | --- |
| `usuarios` | Tecnicos, proveedores, registro, login, perfiles y moderacion | Django auth |
| `catalogo` | Productos, busqueda y gestion del catalogo | `usuarios` |
| `creditos` | Limites, saldos, deudas y emails de credito | `usuarios`; consulta pedidos desde sus vistas |
| `pedidos` | Solicitudes, estados, pagos, exportacion y emails de pedidos | `usuarios`, `catalogo`, `creditos` |
| `calificaciones` | Opiniones de tecnicos y proveedores | `usuarios`, `pedidos` |
| `core` | Inicio, dashboard, 404, layout, assets y datos de demostracion | Compone las apps de dominio |

Cada app expone sus rutas desde `urls.py`. `config/urls.py` incluye todos esos
modulos sin namespace, por lo que nombres como `crear_pedido`, `mis_creditos` y
`dashboard` se mantienen estables.

## Donde buscar cada cambio

El recorrido habitual de una funcionalidad es `urls.py` -> `views.py` ->
`forms.py` -> `models.py` -> `templates/<app>/`. Cada modelo se registra en el
`admin.py` de su propia app y posee una migracion inicial local.

- Autenticacion, perfiles, aprobacion y permisos: `usuarios/`.
- Productos, filtros y busqueda: `catalogo/`.
- Ciclo de compra, comprobantes y exportacion: `pedidos/`.
- Limites y deuda comercial: `creditos/`.
- Calificaciones posteriores a pedidos completados: `calificaciones/`.
- Paginas que componen varios dominios: `core/`.

Los helpers de rol y aprobacion viven en `usuarios/utils.py`. El calculo de
distancia pertenece a `catalogo/utils.py`. Los emails se dividen entre
`pedidos/notifications.py` y `creditos/notifications.py`. El contador global de
pedidos pendientes se configura desde `pedidos/context_processors.py`.

## Templates, static y media

Los templates usan el namespace de su app, por ejemplo
`pedidos/crear_pedido.html`, y extienden `core/base.html`. Los mapas, logos y
otros assets compartidos viven en `core/static/core/`. `media/` conserva las
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

Las pruebas se distribuyen por app. `core/tests.py` contiene escenarios de
integracion transversal y 404; `usuarios/tests.py` cubre acceso y perfiles;
`pedidos/tests.py` cubre el ciclo de pedido y sus notificaciones.

El comando `crear_usuarios_prueba`, ubicado en `core/management/commands/`, crea
los tres roles de demostracion y datos relacionados de varias apps. La opcion
`--reset` elimina y vuelve a generar solo esos datos de prueba.

## Checklist para nuevas funcionalidades

1. Elegir la app propietaria por responsabilidad, no por la pantalla desde la que se accede.
2. Modificar modelo y migracion dentro de esa app si cambia la persistencia.
3. Mantener formulario, vista, template, admin y pruebas junto al dominio.
4. Importar modelos desde su app propietaria y evitar fachadas globales.
5. Agregar la ruta al `urls.py` local; conservar nombres publicos existentes.
6. Ejecutar checks, migraciones pendientes y toda la suite antes de entregar.
