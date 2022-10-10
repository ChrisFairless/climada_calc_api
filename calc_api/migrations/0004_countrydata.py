# Generated by Django 4.0 on 2022-10-10 00:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc_api', '0003_measure_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_name', models.CharField(max_length=60)),
                ('country_iso3alpha', models.CharField(max_length=3)),
                ('population', models.IntegerField()),
                ('socvuln_min', models.FloatField()),
                ('socvuln_max', models.FloatField()),
            ],
        ),
    ]