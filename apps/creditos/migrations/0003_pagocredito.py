from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('creditos', '0002_credito_ciclo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagoCredito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('ciclo', models.PositiveIntegerField()),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente de confirmación'), ('confirmado', 'Confirmado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=15)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_resolucion', models.DateTimeField(blank=True, null=True)),
                ('credito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos', to='creditos.credito')),
            ],
            options={'ordering': ['-fecha_creacion']},
        ),
    ]
