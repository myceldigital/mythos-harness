set shell := ["zsh", "-cu"]

default:
  @just --list

install:
  python3 -m pip install -e ".[dev]"

run:
  uvicorn mythos_harness.main:app --host 0.0.0.0 --port 8080 --reload

test:
  python3 -m pytest -q

lint:
  python3 -m compileall src

bootstrap-postgres:
  psql "$MYTHOS_POSTGRES_DSN" -f sql/bootstrap_postgres.sql

migrate-vector-16-to-1536:
  psql "$MYTHOS_POSTGRES_DSN" -f sql/migrations/20260422_vector_16_to_1536.sql

migrate:
  python3 scripts/apply_migrations.py --dsn "$MYTHOS_POSTGRES_DSN" --schema "${MYTHOS_POSTGRES_SCHEMA:-mythos}"
