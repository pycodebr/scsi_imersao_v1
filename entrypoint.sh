#!/bin/sh
set -e

# Aplica migrações e coleta estáticos antes de iniciar o processo.
# O comando final (app: runserver | celery_worker | celery_beat) é injetado
# pelo `command:` de cada serviço no docker-compose e executado via `exec "$@"`.
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
