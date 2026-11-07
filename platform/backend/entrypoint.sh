#!/bin/sh
set -eu

DB_PASSWORD="$(cat /run/secrets/db_password)"
SECRET_KEY="$(cat /run/secrets/secret_key)"
OWNER_PASSWORD="$(cat /run/secrets/owner_password)"
export DATABASE_URL="postgresql+psycopg://shveya:${DB_PASSWORD}@db:5432/shveya"
export SECRET_KEY OWNER_PASSWORD
export OWNER_EMAIL="${OWNER_EMAIL:-owner@localhost.local}"

alembic upgrade head
python -m app.initial_data
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
