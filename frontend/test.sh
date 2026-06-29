#!/bin/sh
set -e

echo "Running prettier check..."
yarn prettier:check

echo "Running ESLint..."
yarn lint

echo "Running frontend tests..."
yarn test:coverage
