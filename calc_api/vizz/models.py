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
