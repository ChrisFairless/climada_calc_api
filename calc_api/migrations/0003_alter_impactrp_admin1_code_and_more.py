# Generated by Django 4.0 on 2022-05-22 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc_api', '0002_exposures_hazard_impactrp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='impactrp',
            name='admin1_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='impactrp',
            name='admin2_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='impactrp',
            name='poly',
            field=models.TextField(blank=True),
        ),
    ]
