"""
Django settings for climada_calc project.

Generated by 'django-admin startproject' using Django 3.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
#DEBUG = True
DEBUG = os.environ.get('DEBUG', '') != 'False'

ALLOWED_HOSTS = []
ALLOWED_HOSTS.extend(filter(None, os.environ.get('ALLOWED_HOSTS', '').split(',')))

# Application definition

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'calc_api.apps.CalcApiConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'ninja',
    'corsheaders'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'climada_calc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'climada_calc.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
# TODO switch over to postgres
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Cache
# https://docs.djangoproject.com/en/4.0/topics/cache/
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL')
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "staticfiles"
]
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"


# Celery configuration
# All of the configurable options are in climada_calc-config.yaml
#TODO switch back to rabbitmq   --- also does the above need '/0' at the end?
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') + '/0'
#CELERY_RESULT_BACKEND = "db+sqlite:////climada_calc_api/celery.sqlite3"
CELERY_CACHE_BACKEND = 'default'
#TODO switch back to rabbitmq
#CELERY_BROKER_URL = 'amqp://rabbittest:fasthydrantpotter@127.0.0.1:5672//'
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_BROKER_POOL_LIMIT = 8
CELERY_REDIS_MAX_CONNECTIONS = 8
CELERY_ACCEPT_CONTENT = ['application/json', 'application/x-python-serialize']
CELERY_TASK_SERIALIZER = 'pickle'  # TODO Get this working with json
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_TASK_TIME_LIMIT: 10 * 60
CELERY_IMPORTS = ['calc_api.vtest.ninja', 'calc_api.vizz.ninja']

CELERY_SINGLETON_BACKEND_URL = os.environ.get('REDIS_URL') + '/0'
CELERY_SINGLETON_LOCK_EXPIRY = 300


# Geocoding
GEOCODE_URL = os.environ.get('GEOCODE_URL')


# CORS
CORS_ALLOW_ALL_ORIGINS = True
