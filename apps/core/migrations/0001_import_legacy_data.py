from django.core.management.color import no_style
from django.db import migrations


LEGACY_TABLES = (
    (
        'plataforma_tecnico',
        'usuarios_tecnico',
        (
            'id', 'especialidad', 'ubicacion', 'usuario_id', 'cuit',
            'is_approved', 'estado', 'nota_admin', 'telefono',
            'email_confirmed', 'latitud', 'longitud',
        ),
    ),
    (
        'plataforma_proveedor',
        'usuarios_proveedor',
        (
            'id', 'nombre_negocio', 'direccion', 'rubro', 'usuario_id',
            'cuit', 'is_approved', 'estado', 'horarios', 'imagen', 'logo',
            'nota_admin', 'latitud', 'longitud', 'email_confirmed',
            'alias_transferencia', 'banco_transferencia',
            'cbu_transferencia', 'titular_transferencia',
        ),
    ),
    (
        'plataforma_producto',
        'catalogo_producto',
        (
            'id', 'nombre', 'categoria', 'precio', 'disponible',
            'proveedor_id', 'modelo', 'stock', 'descripcion', 'imagen',
        ),
    ),
    (
        'plataforma_credito',
        'creditos_credito',
        (
            'id', 'limite', 'saldo_usado', 'proveedor_id', 'tecnico_id',
            'activo', 'fecha_creacion',
        ),
    ),
    (
        'plataforma_pedido',
        'pedidos_pedido',
        (
            'id', 'cantidad', 'forma_entrega', 'estado', 'monto_total',
            'fecha_creacion', 'fecha_actualizacion', 'notas', 'producto_id',
            'proveedor_id', 'tecnico_id', 'respuesta_proveedor',
            'usa_credito', 'forma_pago', 'comprobante_transferencia',
        ),
    ),
    (
        'plataforma_calificacionproveedor',
        'calificaciones_calificacionproveedor',
        (
            'id', 'estrellas', 'comentario', 'fecha_creacion', 'pedido_id',
            'proveedor_id', 'tecnico_id',
        ),
    ),
    (
        'plataforma_calificaciontecnico',
        'calificaciones_calificaciontecnico',
        (
            'id', 'puntualidad', 'trato', 'comentario_privado',
            'fecha_creacion', 'pedido_id', 'proveedor_id', 'tecnico_id',
        ),
    ),
)


def import_legacy_data(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    quote = connection.ops.quote_name

    with connection.cursor() as cursor:
        for source, target, columns in LEGACY_TABLES:
            if source not in existing_tables or target not in existing_tables:
                continue

            column_sql = ', '.join(quote(column) for column in columns)
            cursor.execute(
                f'INSERT INTO {quote(target)} ({column_sql}) '
                f'SELECT {column_sql} FROM {quote(source)} '
                f'ON CONFLICT DO NOTHING'
            )

        models = [
            apps.get_model('usuarios', 'Tecnico'),
            apps.get_model('usuarios', 'Proveedor'),
            apps.get_model('catalogo', 'Producto'),
            apps.get_model('creditos', 'Credito'),
            apps.get_model('pedidos', 'Pedido'),
            apps.get_model('calificaciones', 'CalificacionProveedor'),
            apps.get_model('calificaciones', 'CalificacionTecnico'),
        ]
        for sql in connection.ops.sequence_reset_sql(no_style(), models):
            cursor.execute(sql)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('usuarios', '0001_initial'),
        ('catalogo', '0001_initial'),
        ('creditos', '0001_initial'),
        ('pedidos', '0001_initial'),
        ('calificaciones', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(import_legacy_data, migrations.RunPython.noop),
    ]

