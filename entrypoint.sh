#!/bin/bash

echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U postgres; do
    sleep 1
done
echo "PostgreSQL is ready!"

python3 create_db.py

python3 run.py
