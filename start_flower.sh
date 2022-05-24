#!/bin/sh

until timeout 10s celery -A calc_api inspect ping; do
    >&2 echo "Celery workers not available"
done

echo 'Starting flower'
celery -A calc_api flower
