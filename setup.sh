#!/bin/bash
# python manage.py makemigrations --noinput
# python manage.py migrate --noinput
# python manage.py makemigrations django_celery_results --noinput
# python manage.py migrate django_celery_results --noinput
# python manage.py generate_sample_data
# python manage.py generate_measure_data
python manage.py collectstatic --noinput
