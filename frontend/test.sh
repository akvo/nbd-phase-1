#!/bin/sh
set -e

echo "Running prettier check..."
npm run prettier:check

echo "Running ESLint..."
npm run lint

echo "Running frontend tests..."
npm run test:coverage
