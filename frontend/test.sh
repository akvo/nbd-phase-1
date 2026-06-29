#!/bin/sh
set -e

echo "Running prettier check..."
yarn prettier:check || (echo "Prettier check failed! Showing diffs:" && npx prettier --diff src/components/ui/site-drawer.tsx src/components/ui/site-drawer/parameter-table.tsx src/components/ui/site-drawer/score-breakdown-panel.tsx && exit 1)

echo "Running ESLint..."
yarn lint

echo "Running frontend tests..."
yarn test:coverage
