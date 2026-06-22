#!/bin/bash
# Test rate limiting on /api/v1/sites
# Usage: ./test_rate_limit.sh [num_requests] [url]

NUM_REQUESTS="${1:-70}"
URL="${2:-http://localhost:3000/api/v1/sites}"

echo "Sending $NUM_REQUESTS requests to $URL"
echo "----------------------------------------"

for i in $(seq 1 "$NUM_REQUESTS"); do
  {
    body=$(curl -s -w "\n%{http_code}" "$URL")
    status=$(echo "$body" | tail -1)
    echo "req $i -> status=$status"
    if [ "$status" = "429" ]; then
      echo "  body: $(echo "$body" | sed '$d')"
    fi
  } &
done
wait

echo "----------------------------------------"
echo "Done."