#!/bin/bash

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
    sleep 1
done
echo "PostgreSQL is ready!"

python3 create_db.py

gunicorn --bind 0.0.0.0:8080 run:app
