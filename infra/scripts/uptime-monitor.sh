#!/bin/bash
set -euo pipefail

HEALTH_URL="${1:-http://localhost:8000/health}"
LOG_FILE="${2:-/var/log/portfolio-uptime.log}"
TIMESTAMP=$(date +%Y-%m-%d_%H:%M:%S)

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$HEALTH_URL" || echo "-1")

if [ "$STATUS" = "200" ]; then
    echo "$TIMESTAMP | UP | ${RESPONSE_TIME}s | $HEALTH_URL" >> "$LOG_FILE"
else
    echo "$TIMESTAMP | DOWN ($STATUS) | ${RESPONSE_TIME}s | $HEALTH_URL" >> "$LOG_FILE"
fi

# Trim log to last 10000 lines
tail -n 10000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"