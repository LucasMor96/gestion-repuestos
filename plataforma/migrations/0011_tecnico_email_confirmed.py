from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0010_credito_campos_pedido_usa_credito'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        (
                            'ALTER TABLE plataforma_tecnico '
                            'ADD COLUMN IF NOT EXISTS email_confirmed boolean'
                        ),
                        (
                            'UPDATE plataforma_tecnico '
                            'SET email_confirmed = false '
                            'WHERE email_confirmed IS NULL'
                        ),
                        (
                            'ALTER TABLE plataforma_tecnico '
                            'ALTER COLUMN email_confirmed SET DEFAULT false'
                        ),
                        (
                            'ALTER TABLE plataforma_tecnico '
                            'ALTER COLUMN email_confirmed SET NOT NULL'
                        ),
                    ],
                    reverse_sql=[
                        (
                            'ALTER TABLE plataforma_tecnico '
                            'DROP COLUMN IF EXISTS email_confirmed'
                        ),
                    ],
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='tecnico',
                    name='email_confirmed',
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]
