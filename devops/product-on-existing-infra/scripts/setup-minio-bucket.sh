#!/bin/bash
# Create MinIO bucket with verification
# Usage: ./setup-minio-bucket.sh <bucket-name>

set -e

BUCKET_NAME="${1:?Usage: $0 <bucket-name>}"

echo "Creating MinIO bucket: ${BUCKET_NAME}"

# Create bucket
docker exec iacgenie_minio mc alias set local http://127.0.0.1:9000 iacgenie-minio "${MINIO_SECRET_KEY:-CHANGE_ME}" 2>/dev/null || true
docker exec iacgenie_minio mc mb "local/${BUCKET_NAME}" 2>/dev/null || echo "Bucket may already exist"

# Verify
echo "Listing buckets:"
docker exec iacgenie_minio mc ls local/

echo "✅ Bucket '${BUCKET_NAME}' ready."
