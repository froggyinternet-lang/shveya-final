#!/bin/bash
# scripts/check_grant.sh — проверка что влезаем в грант 10к и b2.medium 4GB

echo "=== SHVEYA GRANT CHECK b2.medium ==="
echo "Дата: $(date)"
echo ""

echo "[1] RAM хоста:"
free -h
echo ""

echo "[2] Docker stats (лимиты):"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemLimit}}\t{{.CPUPerc}}"
echo ""

echo "[3] docker-compose ps:"
docker compose ps
echo ""

echo "[4] Ожидаемые лимиты (должно быть < 4GB):"
echo "  postgres: 512MB limit, 256M reservation"
echo "  api: 1024MB limit, 512M reservation"
echo "  bot: 512MB limit, 256M reservation"
echo "  TOTAL LIMIT: 2048MB -> запас 2GB под OS + docker"
echo ""

echo "[5] Проверка .env:"
if [ -f .env ]; then
  echo "  .env exists: OK"
  for k in DATABASE_URL TELEGRAM_BOT_TOKEN YOOKASSA_SHOP_ID YOOKASSA_SECRET_KEY SECRET_KEY; do
    if grep -q "^$k=" .env; then
      v=$(grep "^$k=" .env | cut -d= -f2- | cut -c1-8)
      echo "  $k = ${v}... : OK"
    else
      echo "  $k = MISSING!"
    fi
  done
else
  echo "  .env MISSING!"
fi
echo ""

echo "[6] Диск:"
df -h | grep -E "Filesystem|/dev/vda|/home"
echo ""

echo "[7] Стоимость b2.medium оценка (Yandex Cloud 2025-2026):"
cat <<'COST'
  b2.medium 50% 2x4GB: ~2600-3200 руб/мес
  Диск 32GB SSD: ~800 руб/мес
  Трафик + IP: ~200-500 руб/мес
  ИТОГО: ~3600-4500 руб/мес < 6500 лимита
  Грант 10к хватит на ~2 месяца, цель 1.5 мес с запасом
COST
echo ""

echo "[8] Проверка миграции:"
if docker compose exec -T postgres psql -U ${POSTGRES_USER:-shveya} -d ${POSTGRES_DB:-shveya} -c "\dt" 2>/dev/null | grep -q "orders\|users"; then
  echo "  Tables exist: OK"
  docker compose exec -T postgres psql -U ${POSTGRES_USER:-shveya} -d ${POSTGRES_DB:-shveya} -c "\dt"
else
  echo "  Tables NOT FOUND — накати миграцию:"
  echo "  cat мозг/03_TASKS/migrations/001_initial_final.sql | docker compose exec -T postgres psql -U shveya -d shveya"
fi
echo ""

echo "=== GRANT CHECK DONE ==="
if free -m | awk '/Mem:/ {if ($2 < 3500) exit 1}'; then
  echo "PASS: RAM >= 3.5GB"
else
  echo "FAIL: RAM < 3.5GB — ты не на b2.medium?"
fi
