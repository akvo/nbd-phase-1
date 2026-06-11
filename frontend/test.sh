#!/usr/bin/env bash
set -exuo pipefail

echo "Running frontend tests..."
yarn test:coverage
