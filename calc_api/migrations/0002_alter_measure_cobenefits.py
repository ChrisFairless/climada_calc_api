# Generated by Django 4.0 on 2022-09-25 18:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc_api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='measure',
            name='cobenefits',
            field=models.ManyToManyField(null=True, to='calc_api.Cobenefit'),
        ),
    ]
