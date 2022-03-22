import datetime as dt
import uuid

from django.db import models
from django.utils.timezone import utc

class Job(models.Model):
    job_id = models.TextField(primary_key=True)
    location = models.TextField()
    status = models.TextField()
    request = models.JSONField()
    submitted_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    runtime = models.FloatField(null=True)
    response = models.JSONField(null=True)
    response_uri = models.URLField(null=True)
    code = models.IntegerField(null=True)
    message = models.TextField(null=True)


class Cobenefit(models.Model):
    value = models.TextField(primary_key=True)
    name = models.TextField()
    description = models.TextField(null=True)


class Measure(models.Model):
    name = models.TextField()
    description = models.TextField(null=True)
    hazard_type = models.TextField()
    cost_type = models.TextField(default="whole_project")
    cost = models.FloatField()
    annual_upkeep = models.FloatField(default=0)
    priority = models.TextField(default="even_coverage")
    percentage_coverage = models.FloatField(default=100)
    percentage_effectiveness = models.FloatField(default=100)
    is_coastal = models.BooleanField(default=False)
    max_distance_from_coast = models.FloatField(null=True)
    hazard_cutoff = models.FloatField(null=True)
    return_period_cutoff = models.FloatField(null=True)
    hazard_change_multiplier = models.FloatField(null=True)
    hazard_change_constant = models.FloatField(null=True)
    cobenefits = models.ManyToManyField(Cobenefit)
    units_currency = models.TextField()
    units_hazard = models.TextField()
    units_distance = models.TextField()


class FileCache(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.TextField(unique=True)
    function = models.TextField()
    args = models.TextField(null=True)
    kargs = models.TextField(null=True)
    path = models.TextField(null=True)
    locked = models.BooleanField()

    class Meta:
        db_table = 'file_cache'

    def __str__(self):
        return f"{self.function}({self.args},{self.kargs}) -> {self.path}"
