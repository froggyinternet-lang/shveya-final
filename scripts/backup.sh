#!/bin/bash
set -e
# scripts/backup.sh — бэкап postgres для b2.medium

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/shveya_${DATE}.sql.gz"

echo "=== Backup $FILE ==="

# .env загрузка
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

POSTGRES_USER=${POSTGRES_USER:-shveya}
POSTGRES_DB=${POSTGRES_DB:-shveya}

docker compose exec -T postgres pg_dump -U $POSTGRES_USER -d $POSTGRES_DB | gzip > "$FILE"

echo "Backup size: $(du -h $FILE | cut -f1)"
echo "Saved to $FILE"

# оставляем последние 7 бэкапов
ls -t $BACKUP_DIR/*.gz | tail -n +8 | xargs -r rm -v

# опционально: заливка в S3
# aws s3 cp $FILE s3://$S3_BUCKET/backups/ --endpoint-url $S3_ENDPOINT

echo "=== DONE ==="
