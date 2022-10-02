from django.contrib import admin
from .models import (Cobenefit, Measure, JobLog)

admin.site.site_title = 'CLIMADA calc api admin'
admin.site.site_header = 'CLIMADA calc api admin'

# Register your models here.
admin.site.register(Cobenefit)
admin.site.register(Measure)
admin.site.register(JobLog)
