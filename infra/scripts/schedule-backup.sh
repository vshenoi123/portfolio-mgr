#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$PROJECT_DIR/backend/.env"

# Source environment variables for OCI
set -a
source "$ENV_FILE"
set +a

CRON_EXPR="0 4 * * *"
CRON_JOB="$CRON_EXPR cd $PROJECT_DIR && OCI_BUCKET_NAMESPACE=\"$OCI_BUCKET_NAMESPACE\" OCI_BUCKET_NAME=\"$OCI_BUCKET_NAME\" OCI_REGION=\"$OCI_REGION\" DATA_DIR=\"$DATA_DIR\" bash infra/scripts/backup-to-oci.sh >> /var/log/portfolio-backup.log 2>&1"

(crontab -l 2>/dev/null | grep -v "backup-to-oci" || true; echo "$CRON_JOB") | crontab -

echo "Daily backup cron installed (4 AM UTC, 90-day retention)."