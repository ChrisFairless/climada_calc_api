# Generated by Django 4.0 on 2022-10-06 08:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc_api', '0002_alter_measure_cobenefits'),
    ]

    operations = [
        migrations.AddField(
            model_name='measure',
            name='slug',
            field=models.TextField(null=True),
        ),
    ]