from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def restriccion_email():
    # El User de Django permite cuentas administrativas sin email.
    return models.UniqueConstraint(
        Lower(Trim('email')),
        condition=~models.Q(email=''),
        name='usuarios_email_normalizado_unico',
    )


def normalizar_emails(apps, schema_editor):
    Usuario = apps.get_model('auth', 'User')
    usuarios = Usuario.objects.using(schema_editor.connection.alias)
    duplicados = usuarios.annotate(
        email_normalizado=Lower(Trim('email')),
    ).exclude(email_normalizado='').values('email_normalizado').annotate(
        cantidad=models.Count('pk'),
    ).filter(cantidad__gt=1)
    if duplicados.exists():
        raise RuntimeError(
            'Hay cuentas con el mismo email sin distinguir mayusculas o espacios. '
            'Corregi esos emails antes de aplicar la migracion; no se elimino ninguna cuenta.'
        )
    # No cambia usernames, claves, IDs ni relaciones de las cuentas existentes.
    usuarios.update(email=Lower(Trim('email')))


def agregar_restriccion(apps, schema_editor):
    schema_editor.add_constraint(apps.get_model('auth', 'User'), restriccion_email())


def quitar_restriccion(apps, schema_editor):
    schema_editor.remove_constraint(apps.get_model('auth', 'User'), restriccion_email())


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('usuarios', '0002_respuestamoderacion_imagenmoderacion'),
    ]

    operations = [
        migrations.RunPython(normalizar_emails, migrations.RunPython.noop),
        # Restriccion adicional sobre auth.User, sin modificar el paquete de Django
        # ni reemplazar el modelo de usuario en una base que ya tiene relaciones.
        migrations.RunPython(agregar_restriccion, quitar_restriccion),
    ]
