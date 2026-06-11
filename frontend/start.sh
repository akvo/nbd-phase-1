#!/bin/sh
set -e

# Install dependencies if in development mode
if [ "$NODE_ENV" != "production" ] && [ "$NODE_ENV" != "prod" ] && [ "$APP_ENV" != "staging" ] && [ "$APP_ENV" != "test" ]; then
  echo "Installing Node dependencies (Development mode)..."
  yarn install
fi

# Run custom command if provided
if [ $# -gt 0 ]; then
  echo "Running custom command: $@"
  exec "$@"
fi

if [ "$NODE_ENV" = "production" ] || [ "$NODE_ENV" = "prod" ] || [ "$APP_ENV" = "staging" ] || [ "$APP_ENV" = "test" ]; then
  echo "Starting Next.js frontend in PRODUCTION mode..."
  exec yarn start
else
  echo "Starting Next.js frontend in DEVELOPMENT mode..."
  exec yarn dev
fi
