import django.db.models.deletion
from django.db import migrations, models


def normalizar_respuestas_anteriores(apps, schema_editor):
    Pedido = apps.get_model('pedidos', 'Pedido')
    Producto = apps.get_model('catalogo', 'Producto')
    Pedido.objects.filter(respuesta_proveedor='Confirmado para demo.').update(
        respuesta_proveedor=None,
    )

    prefijo = 'Alternativa propuesta: Producto ofrecido: '
    separador_precio = '. Precio unitario: $'
    propuestas = Pedido.objects.filter(respuesta_proveedor__startswith=prefijo)
    for pedido in propuestas.iterator():
        detalle = pedido.respuesta_proveedor[len(prefijo):]
        if separador_precio not in detalle:
            continue
        etiqueta_producto, detalle_precio = detalle.split(separador_precio, 1)
        producto_encontrado = None
        for producto in Producto.objects.filter(proveedor_id=pedido.proveedor_id):
            etiqueta = (
                f'{producto.nombre} ({producto.modelo})'
                if producto.modelo else producto.nombre
            )
            if etiqueta == etiqueta_producto:
                producto_encontrado = producto
                break
        if producto_encontrado is None:
            continue
        partes = detalle_precio.split('. ', 1)
        mensaje = partes[1].strip() if len(partes) == 2 else ''
        pedido.producto_alternativo_id = producto_encontrado.pk
        pedido.respuesta_proveedor = mensaje or None
        pedido.save(update_fields=['producto_alternativo', 'respuesta_proveedor'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0001_initial'),
        ('pedidos', '0004_proteger_historial_productos'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='producto_alternativo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pedidos_como_alternativa',
                to='catalogo.producto',
            ),
        ),
        migrations.RunPython(normalizar_respuestas_anteriores, migrations.RunPython.noop),
    ]
