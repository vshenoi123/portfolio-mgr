#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/portfolio-backup-${TIMESTAMP}.tar.gz"

echo "Starting backup at $TIMESTAMP..."

# Compress data directory (Parquet + DuckDB)
tar -czf "$BACKUP_FILE" \
    -C "$(dirname "$DATA_DIR")" \
    "$(basename "$DATA_DIR")"

# Upload to OCI Object Storage
oci os object put \
    --namespace "$OCI_BUCKET_NAMESPACE" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --file "$BACKUP_FILE" \
    --name "backups/daily/$(date +%Y/%m)/portfolio-${TIMESTAMP}.tar.gz" \
    --region "$OCI_REGION"

# Cleanup local backup
rm -f "$BACKUP_FILE"

# Prune backups older than 90 days
BACKUP_PREFIX="backups/daily"
OLDER_THAN=$(date -d "-90 days" +%Y/%m/%d)
oci os object list \
    --namespace "$OCI_BUCKET_NAMESPACE" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --prefix "$BACKUP_PREFIX" \
    --region "$OCI_REGION" \
    --query "data[?contains(name,'${OLDER_THAN}')].name" \
    --raw-output | while IFS= read -r obj; do
    oci os object delete \
        --namespace "$OCI_BUCKET_NAMESPACE" \
        --bucket-name "$OCI_BUCKET_NAME" \
        --object-name "$obj" \
        --region "$OCI_REGION" \
        --force
done

echo "Backup complete: $BACKUP_FILE uploaded, old backups pruned."