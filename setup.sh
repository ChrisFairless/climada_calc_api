#!/bin/bash
python manage.py makemigrations calc_api --noinput
python manage.py migrate calc_api --noinput
python manage.py makemigrations django_celery_results --noinput
python manage.py migrate django_celery_results --noinput
python manage.py collectstatic --noinput
