#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "Postgres is ready!"

echo "Running migrations..."
uv run python -m lib.scripts.migrate

echo "Starting application..."
exec "$@"
