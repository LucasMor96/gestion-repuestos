from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0012_tecnico_latitud_tecnico_longitud'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        (
                            'ALTER TABLE plataforma_proveedor '
                            'ADD COLUMN IF NOT EXISTS email_confirmed boolean'
                        ),
                        (
                            'UPDATE plataforma_proveedor '
                            'SET email_confirmed = false '
                            'WHERE email_confirmed IS NULL'
                        ),
                        (
                            'ALTER TABLE plataforma_proveedor '
                            'ALTER COLUMN email_confirmed SET DEFAULT false'
                        ),
                        (
                            'ALTER TABLE plataforma_proveedor '
                            'ALTER COLUMN email_confirmed SET NOT NULL'
                        ),
                    ],
                    reverse_sql=[
                        (
                            'ALTER TABLE plataforma_proveedor '
                            'DROP COLUMN IF EXISTS email_confirmed'
                        ),
                    ],
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='proveedor',
                    name='email_confirmed',
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]
