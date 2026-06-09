# Generated manually for DIECISEISAVOS fase choice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prode', '0002_alter_partido_equipo_local_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partido',
            name='fase',
            field=models.CharField(
                choices=[
                    ('GRUPOS', 'Fase de Grupos'),
                    ('DIECISEISAVOS', '16avos de Final'),
                    ('OCTAVOS', '8avos de Final'),
                    ('CUARTOS', '4tos de Final'),
                    ('SEMI', 'Semifinal'),
                    ('TERCERO', 'Tercer Puesto'),
                    ('FINAL', 'Final'),
                ],
                default='GRUPOS',
                max_length=15,
            ),
        ),
    ]
