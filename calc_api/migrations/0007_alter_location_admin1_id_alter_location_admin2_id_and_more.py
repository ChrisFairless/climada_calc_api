# Generated by Django 4.0 on 2023-02-27 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc_api', '0006_alter_joblog_func_alter_joblog_job_hash_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='admin1_id',
            field=models.CharField(max_length=60, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='admin2_id',
            field=models.CharField(max_length=60, null=True),
        ),
        migrations.AlterField(
            model_name='location',
            name='scale',
            field=models.CharField(max_length=60, null=True),
        ),
    ]
