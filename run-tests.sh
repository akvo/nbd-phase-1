#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m'

echo "Running flake8 linting..."
./dc.sh exec backend python -m flake8 app/ tests/

echo -e "${GREEN}=== Running Backend Tests & Coverage ===${NC}"
./dc.sh exec backend python -m pytest

echo -e "\n${GREEN}=== Running Frontend Tests & Coverage ===${NC}"
./dc.sh exec frontend yarn test:coverage
