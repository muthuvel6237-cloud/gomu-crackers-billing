import os
from pathlib import Path

from .runtime_paths import (
    app_data_root,
    ensure_directory,
    ensure_file,
    is_frozen,
    is_railway,
    resource_path,
    resource_root,
)

BASE_DIR = resource_root()
APP_DATA_DIR = app_data_root()

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-!x(g+3cuil95j%%qlhx@^ky5t(o-*qwxdslt2ed$$=u&693v57'
)

DEBUG = os.environ.get('DJANGO_DEBUG', '0' if is_frozen() else '1').lower() in {'1', 'true', 'yes', 'on'}

# Allow Railway domains + localhost for development.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        '127.0.0.1,localhost,.up.railway.app,.railway.app',
    ).split(',')
    if host.strip()
]

# CSRF trusted origins for Railway deployment
CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
    'https://*.railway.app',
]
csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in csrf_origins.split(',')
        if origin.strip()
    ]

railway_public_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if railway_public_domain:
    CSRF_TRUSTED_ORIGINS.append(f'https://{railway_public_domain}')

if is_railway():
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', '1').lower() in {
        '1',
        'true',
        'yes',
        'on',
    }
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'billing_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gomu_crackers.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            path for path in [
                resource_path('templates'),
                resource_path('billing_app', 'templates'),
            ] if path.exists()
        ],
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

WSGI_APPLICATION = 'gomu_crackers.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ensure_file('db.sqlite3'),
    }
}

# Use DATABASE_URL if provided (for Railway PostgreSQL or other cloud databases)
import dj_database_url
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(default=DATABASE_URL, conn_max_age=600)


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    path for path in [
        resource_path('static'),
        resource_path('billing_app', 'static'),
    ] if path.exists()
]
STATIC_ROOT = ensure_directory('staticfiles')

# WhiteNoise for serving static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = APP_DATA_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
