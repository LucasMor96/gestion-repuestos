from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0009_restringir_rubros_dos_categorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='credito',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='credito',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pedido',
            name='usa_credito',
            field=models.BooleanField(default=False),
        ),
    ]
