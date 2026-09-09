from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('pedidos', '0005_pedido_producto_alternativo')]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='forma_pago',
            field=models.CharField(
                choices=[
                    ('transferencia', 'Transferencia bancaria'),
                    ('credito_comercial', 'Credito comercial'),
                    ('solicitud_credito', 'Solicitud de crédito'),
                ],
                default='transferencia',
                max_length=25,
            ),
        ),
    ]
