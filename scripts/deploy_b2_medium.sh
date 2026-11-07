#!/bin/bash
set -e
# scripts/deploy_b2_medium.sh — деплой на b2.medium для гранта 10к

echo "=== SHVEYA deploy b2.medium ==="
echo "PWD: $(pwd)"

if [ ! -f docker-compose.yml ]; then
  echo "ERR: docker-compose.yml не найден. Запусти из корня C:\Perm_Repair\ / ~/shveya"
  exit 1
fi

if [ ! -f .env ]; then
  echo "WARN: .env не найден, копирую из .env.example"
  cp .env.example .env
  echo ">>> ОТРЕДАКТИРУЙ .env! nano .env"
  exit 1
fi

echo "[1/5] build..."
docker compose build --no-cache

echo "[2/5] up -d postgres..."
docker compose up -d postgres
echo "Ждем postgres health..."
until docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-shveya} -d ${POSTGRES_DB:-shveya}; do
  sleep 2
done

echo "[3/5] миграции..."
MIG_FILE="мозг/03_TASKS/migrations/001_initial_final.sql"
if [ ! -f "$MIG_FILE" ]; then
  MIG_FILE="./migrations/001_initial_final.sql"
fi
if [ -f "$MIG_FILE" ]; then
  echo "Накатываю $MIG_FILE"
  cat "$MIG_FILE" | docker compose exec -T postgres psql -U ${POSTGRES_USER:-shveya} -d ${POSTGRES_DB:-shveya} -v ON_ERROR_STOP=1
else
  echo "WARN: $MIG_FILE не найден, пропускаю миграцию"
fi

echo "[4/5] up -d api bot..."
docker compose up -d api bot

echo "[5/5] status..."
docker compose ps
docker stats --no-stream
echo ""
echo "API docs: http://$(curl -s ifconfig.me 2>/dev/null || echo localhost):8000/docs"
echo "Health: curl http://localhost:8000/health"
echo "Logs: docker compose logs -f"

echo "=== DONE ==="
