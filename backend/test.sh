#!/usr/bin/env bash
set -exuo pipefail

echo "Running flake8 linting..."
python -m flake8 app/ tests/

echo "Running database migrations..."
alembic upgrade head

echo "Running tests..."
python -m pytest
