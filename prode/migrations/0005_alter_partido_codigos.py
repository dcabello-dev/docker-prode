"""Amplía codigo_local/codigo_visitante para códigos tipo gb-eng/gb-wls.

flagcdn usa códigos especiales para Inglaterra (gb-eng) y Gales (gb-wls) que
no entran en varchar(2). Esta migración amplía la columna también en bases
legacy con el esquema viejo.
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


def ampliar_codigos(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        for columna in ('codigo_local', 'codigo_visitante'):
            largo = _longitud_columna(cursor, 'prode_partido', columna)
            if largo is not None and largo < 8:
                cursor.execute(
                    'ALTER TABLE prode_partido '
                    f'ALTER COLUMN {columna} TYPE varchar(8)'
                )


class Migration(migrations.Migration):

    dependencies = [
        ('prode', '0004_alter_partido_zona'),
    ]

    operations = [
        migrations.RunPython(ampliar_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='partido',
            name='codigo_local',
            field=models.CharField(blank=True, max_length=8),
        ),
        migrations.AlterField(
            model_name='partido',
            name='codigo_visitante',
            field=models.CharField(blank=True, max_length=8),
        ),
    ]
