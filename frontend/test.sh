#!/bin/sh
set -e

echo "Running prettier check..."
yarn prettier:check || (
  echo "Prettier check failed! Showing diffs:"
  npx prettier src/components/ui/site-drawer.tsx | diff -u src/components/ui/site-drawer.tsx - || true
  npx prettier src/components/ui/site-drawer/parameter-table.tsx | diff -u src/components/ui/site-drawer/parameter-table.tsx - || true
  npx prettier src/components/ui/site-drawer/score-breakdown-panel.tsx | diff -u src/components/ui/site-drawer/score-breakdown-panel.tsx - || true
  exit 1
)

echo "Running ESLint..."
yarn lint

echo "Running frontend tests..."
yarn test:coverage
