import datetime as dt
import uuid

from django.db import models
from django.utils.timezone import utc


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    request = models.TextField()
    status = models.IntegerField()
    result = models.TextField(null=True)


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
