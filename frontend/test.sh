#!/bin/sh
set -e

echo "Running frontend tests..."
yarn test:coverage
