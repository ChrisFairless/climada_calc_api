from django.contrib import admin
from calc_api.vizz.models import (Cobenefit, Measure)

admin.site.site_title = 'CLIMADA calc api admin'
admin.site.site_header = 'CLIMADA calc api admin'

# Register your models here.
admin.site.register(Cobenefit)
admin.site.register(Measure)
