import datetime as dt
import uuid
import datetime

from django.db import models
from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()


class Job(models.Model):
    job_id = models.TextField(primary_key=True, db_index=True)
    location = models.TextField()
    status = models.TextField()
    request = models.JSONField()
    submitted_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
    runtime = models.FloatField(null=True)
    response = models.JSONField(null=True)
    response_uri = models.URLField(null=True)
    code = models.IntegerField(null=True)
    message = models.TextField(null=True)

    def refresh_expiry(self):
        time_to_expiry = (self.expires_at - datetime.datetime.now()).seconds
        if time_to_expiry < 0.7 * conf.JOB_TIMEOUT:
            new_expiry = datetime.datetime.now() + datetime.timedelta(seconds=conf.JOB_TIMEOUT)
            self.update(expires_at=new_expiry)


class CountryData(models.Model):
    country_name = models.CharField(max_length=60)
    country_iso3alpha = models.CharField(max_length=3)
    population = models.IntegerField()
    socvuln_min = models.FloatField()
    socvuln_max = models.FloatField()


class JobLog(models.Model):
    job_hash = models.CharField(max_length=36, primary_key=True, db_index=True)
    func = models.CharField(max_length=50)
    args = models.TextField()
    kwargs = models.TextField()
    result = models.JSONField(null=True)  # TODO a cleanup cron job that removes these


class Cobenefit(models.Model):
    value = models.TextField(primary_key=True)
    name = models.TextField()
    description = models.TextField(null=True)


class Measure(models.Model):
    name = models.TextField()
    slug = models.TextField(null=True)
    description = models.TextField(null=True)
    hazard_type = models.TextField()
    exposure_type = models.TextField(null=True)
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
    cobenefits = models.ManyToManyField(Cobenefit, null=True)
    units_currency = models.TextField()
    units_hazard = models.TextField()
    units_distance = models.TextField()
    user_generated = models.BooleanField()


class Location(models.Model):
    name = models.TextField(primary_key=True)
    # TODO decide what the ID is for and use it consistently
    id = models.TextField()
    scale = models.CharField(max_length=15, null=True)
    country = models.CharField(max_length=60, null=True)
    country_id = models.CharField(max_length=3, null=True)
    admin1 = models.CharField(max_length=60, null=True)
    admin1_id = models.CharField(max_length=15, null=True)
    admin2 = models.CharField(max_length=60, null=True)
    admin2_id = models.CharField(max_length=15, null=True)
    bbox = models.TextField(null=True)
    poly = models.TextField(null=True)


class Hazard(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField()
    event_id = models.FloatField()
    event_name = models.IntegerField()
    lat = models.FloatField()
    lon = models.FloatField()


class Exposures(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    value = models.FloatField()
    reg_id = models.IntegerField()


class ImpactRP(models.Model):
    id = models.AutoField(primary_key=True)
    haz_uuid = models.UUIDField()
    exp_uuid = models.UUIDField()
    impf_uuid = models.UUIDField(blank=True)
    scaling = models.FloatField(blank=True)
    rp = models.CharField(max_length=4)
    value = models.FloatField()
    country_code = models.CharField(max_length=3, blank=True)
    admin1_code = models.CharField(max_length=20, blank=True)
    admin2_code = models.CharField(max_length=20, blank=True)
    poly = models.TextField(blank=True)
    lat = models.FloatField(blank=True)
    lon = models.FloatField(blank=True)


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
