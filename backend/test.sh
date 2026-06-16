#!/usr/bin/env bash
set -exuo pipefail

echo "Running database migrations..."
alembic upgrade head

echo "Running tests..."
python -m pytest
