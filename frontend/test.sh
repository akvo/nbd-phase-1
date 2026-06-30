#!/bin/sh
set -e

echo "Running prettier check..."
yarn prettier:check || (
  echo "Prettier check failed! Showing formatting differences:"
  npx prettier --list-different . | while read -r file; do
    echo "--- $file"
    npx prettier "$file" | diff -u "$file" - || true
  done
  exit 1
)

echo "Running ESLint..."
yarn lint

echo "Running frontend tests..."
yarn test:coverage
