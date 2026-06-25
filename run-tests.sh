#!/bin/bash
set -e

# Colors for output
CYAN='\033[0;36m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}Running flake8 linting...${NC}"
./dc.sh exec backend python -m flake8 app/ tests/

echo -e "${CYAN}=== Running Backend Tests & Coverage ===${NC}"
./dc.sh exec backend python -m pytest

echo -e "${PURPLE}Running yarn lint...${NC}"
./dc.sh exec frontend yarn lint

echo -e "${BLUE}Running yarn prettier...${NC}"
./dc.sh exec frontend yarn prettier

echo -e "\n${GREEN}=== Running Frontend Tests & Coverage ===${NC}"
./dc.sh exec frontend yarn test:coverage
