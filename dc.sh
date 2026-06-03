#!/bin/bash

# dc.sh - Docker Compose CLI wrapper

set -e

COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.override.yml"

# Help instructions
show_help() {
  echo "Usage: ./dc.sh [command] [options]"
  echo ""
  echo "Commands:"
  echo "  up            Start all docker containers (use -d to run in background)"
  echo "  down          Stop all docker containers and clean up networks"
  echo "  ps            List all running containers"
  echo "  logs          Tail logs of all or specified service (e.g. ./dc.sh logs backend)"
  echo "  exec          Execute command inside a running service (e.g. ./dc.sh exec backend tests)"
  echo "  help          Show this help description"
  echo ""
}

case "$1" in
  up)
    shift
    $COMPOSE_CMD up "$@"
    ;;
  down)
    shift
    $COMPOSE_CMD down "$@"
    ;;
  ps)
    shift
    $COMPOSE_CMD ps "$@"
    ;;
  logs)
    shift
    $COMPOSE_CMD logs -f "$@"
    ;;
  exec)
    shift
    SERVICE="$1"
    shift
    if [ "$SERVICE" = "backend" ] && [ "$1" = "tests" ]; then
      $COMPOSE_CMD exec backend python -m pytest tests/ -v
    elif [ "$SERVICE" = "frontend" ] && [ "$1" = "test" ]; then
      $COMPOSE_CMD exec frontend yarn test
    else
      $COMPOSE_CMD exec "$SERVICE" "$@"
    fi
    ;;
  *)
    show_help
    exit 1
    ;;
esac
