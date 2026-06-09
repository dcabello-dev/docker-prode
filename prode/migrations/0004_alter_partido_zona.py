"""Amplía zona (y fase si hace falta) en PostgreSQL legacy.

En servidores con el esquema viejo, zona puede quedar como varchar(20) aunque
el modelo actual pide 40. Eso rompe cargar_fixture con sedes largas.
"""

from django.db import migrations, models


def _longitud_columna(cursor, tabla, columna):
    cursor.execute(
        """
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        """,
        [tabla, columna],
    )
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0])


def ampliar_columnas_texto(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        zona_len = _longitud_columna(cursor, 'prode_partido', 'zona')
        if zona_len is not None and zona_len < 40:
            cursor.execute(
                'ALTER TABLE prode_partido '
                "ALTER COLUMN zona TYPE varchar(40)"
            )

        fase_len = _longitud_columna(cursor, 'prode_partido', 'fase')
        if fase_len is not None and fase_len < 15:
            cursor.execute(
                'ALTER TABLE prode_partido '
                "ALTER COLUMN fase TYPE varchar(15)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('prode', '0003_alter_partido_fase'),
    ]

    operations = [
        migrations.RunPython(ampliar_columnas_texto, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='partido',
            name='zona',
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
