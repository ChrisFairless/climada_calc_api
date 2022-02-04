import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climada_calc.settings')

app = Celery('climada_calc')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')