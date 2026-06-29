from django.db import migrations, models


def migrar_pedidos_con_credito(apps, schema_editor):
    Pedido = apps.get_model('plataforma', 'Pedido')
    Pedido.objects.filter(usa_credito=True).update(forma_pago='credito_comercial')


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0014_producto_imagen'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='forma_pago',
            field=models.CharField(
                choices=[
                    ('mercadopago', 'MercadoPago (simulado)'),
                    ('transferencia', 'Transferencia bancaria'),
                    ('credito_comercial', 'Credito comercial'),
                ],
                default='transferencia',
                max_length=25,
            ),
        ),
        migrations.RunPython(migrar_pedidos_con_credito, migrations.RunPython.noop),
    ]
