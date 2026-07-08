web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn gomu_crackers.wsgi --bind 0.0.0.0:$PORT
