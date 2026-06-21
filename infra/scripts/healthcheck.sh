#!/bin/bash
set -euo pipefail

ENDPOINT="${1:-http://localhost:8000/health}"
MAX_RETRIES="${2:-30}"
SLEEP_SECONDS="${3:-5}"

echo "Health-checking $ENDPOINT..."

for i in $(seq 1 "$MAX_RETRIES"); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" || true)
    if [ "$STATUS" = "200" ]; then
        echo "OK (attempt $i)"
        exit 0
    fi
    echo "Attempt $i: got $STATUS, retrying in ${SLEEP_SECONDS}s..."
    sleep "$SLEEP_SECONDS"
done

echo "FAILED after $MAX_RETRIES attempts"
exit 1