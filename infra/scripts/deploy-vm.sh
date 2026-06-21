#!/bin/bash
set -euo pipefail

echo "Pulling latest images..."
docker compose pull

echo "Restarting services..."
docker compose up -d --remove-orphans

echo "Running health checks..."
sleep 10
for i in $(seq 1 12); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || true)
    if [ "$STATUS" = "200" ]; then
        echo "Backend healthy (attempt $i)"
        break
    fi
    echo "Attempt $i: got $STATUS, retrying..."
    sleep 5
done

echo "Cleaning up old images..."
docker image prune -f

echo "Deploy complete."