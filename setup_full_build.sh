#!/bin/bash
docker-compose run web python manage.py flush --noinput
docker-compose run web python manage.py makemigrations --noinput
docker-compose run web python manage.py migrate --noinput
docker-compose run web python manage.py makemigrations django_celery_results --noinput
docker-compose run web python manage.py migrate django_celery_results --noinput
# docker-compose run web python manage.py generate_sample_data
docker-compose run web python manage.py generate_measure_data
docker-compose run web python manage.py populate_precalculated_locations_db
docker-compose run web python manage.py collectstatic --noinput
