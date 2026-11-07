# TASK_005 — КУДА РАЗЛОЖИТЬ + ЗАПУСК НА b2.medium (грант 10к)

## Бюджет гранта
- Тариф: **b2.medium** 2 vCPU 50% / 4GB RAM / 32GB SSD
- Лимит: 10 000 руб гранта, цель < 6.5k / мес чтобы пройти на 1.5 мес тестов
- Наша сборка: ~2GB RAM limits (512+1024+512) = влезет в 4GB с запасом под OS

## Куда разложить на локальной машине C:\Perm_Repair\

```
C:\Perm_Repair\
├── мозг/
│   ├── 02_MEMORY/CONTEXT.md
│   ├── 03_TASKS/TASK_005_docker_compose_plan.md
│   └── 03_TASKS/migrations/001_initial_final.sql  <- DDL из TASK_004 (6/6 DONE)
├── api/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   └── models/
│   ├── Dockerfile  <- из TASK_005_ALL/api/Dockerfile
│   └── requirements.txt
├── bot/
│   ├── app/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml  <- из TASK_005_ALL/docker-compose.yml
├── .env  <- скопировать из .env.example и заполнить
├── scripts/
└── MANIFEST.json
```

Инструкция: распакуй `TASK_005_ALL.zip` -> возьми файлы и разложи поверх `C:\Perm_Repair\` с заменой. Структура внутри ZIP уже `TASK_005_ALL/` для проверки, но на сервер кидай корень.

## Что внутри ZIP TASK_005_ALL.zip
- docker-compose.yml оптимизирован под b2.medium
- .env.example
- api/Dockerfile + requirements.txt
- bot/Dockerfile + requirements.txt
- scripts/deploy_b2_medium.sh, backup.sh, check_grant.sh
- MANIFEST.json
- 00_README_КУДА_РАЗЛОЖИТЬ.md (этот файл)

## Развертывание на b2.medium (Ubuntu 22.04)

### 1. Подготовка сервера
```bash
# ssh на b2.medium
ssh yc-user@<IP_B2_MEDIUM>

# docker + compose
sudo apt update && sudo apt install -y docker.io docker-compose-v2 htop
sudo usermod -aG docker $USER
newgrp docker

# клонируем / заливаем проект
# вариант A: scp с Windows
scp -r C:\Perm_Repair\* yc-user@<IP>:/home/yc-user/shveya/

# вариант B: git
git clone <your-repo> shveya && cd shveya
```

### 2. .env
```bash
cd ~/shveya
cp TASK_005_ALL/.env.example .env
nano .env
# заполни:
# DATABASE_URL=postgresql://shveya:***@postgres:5432/shveya
# YOOKASSA_SHOP_ID=...
# YOOKASSA_SECRET_KEY=...
# TELEGRAM_BOT_TOKEN=...
# SECRET_KEY=...
```

### 3. Запуск
```bash
# из корня где лежит docker-compose.yml
docker compose up -d --build
docker compose ps
docker stats --no-stream

# логи
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f postgres
```

### 4. Миграция DDL из TASK_004
Файл: `мозг/03_TASKS/migrations/001_initial_final.sql` — это финальный DDL 6/6 таблиц.

```bash
# способ 1: через контейнер postgres
docker compose exec -T postgres psql -U shveya -d shveya -f /migrations/001_initial_final.sql

# способ 2: если файл локально, скопировать внутрь
docker cp мозг/03_TASKS/migrations/001_initial_final.sql $(docker compose ps -q postgres):/tmp/001.sql
docker compose exec postgres psql -U shveya -d shveya -f /tmp/001.sql

# способ 3: с хоста
cat мозг/03_TASKS/migrations/001_initial_final.sql | docker compose exec -T postgres psql -U shveya -d shveya

# проверка
docker compose exec postgres psql -U shveya -d shveya -c "\dt"
docker compose exec postgres psql -U shveya -d shveya -c "\d+ orders"
```

### 5. Проверка API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### 6. Скрипты
```bash
chmod +x scripts/*.sh
./scripts/check_grant.sh   # проверяет RAM, лимиты, стоимость
./scripts/backup.sh        # делает pg_dump в ./backups/
./scripts/deploy_b2_medium.sh  # полный деплой одной командой
```

## Тюнинг под 4GB

docker-compose.yml уже настроен:
- postgres:15-alpine mem_limit 512M + command: shared_buffers=128MB max_connections=30
- api: mem_limit 1024M + workers 2 (uvicorn)
- bot: mem_limit 512M
- volumes: pgdata (persist)
- network: shveya_net

Остаток ~1.5-2GB под систему и docker daemon.

## Если не влезает
- Уменьши api workers до 1
- Добавь `command: postgres -c work_mem=4MB -c maintenance_work_mem=64MB`
- Выключи логи: `logging: driver: none` для bot на проде

## Грант — как не сжечь
- Не бери b2.small (2GB не хватит для postgres+api)
- Не включай мониторинг / grafana на этом же хосте
- Бекап cron: 0 3 * * * /home/yc-user/shveya/scripts/backup.sh
- check_grant.sh считает пример: b2.medium 50% ~ 2500-3200 руб/мес + диск + трафик = <6.5k

## DONE критерий TASK_005
- [x] ОДИН ZIP TASK_005_ALL.zip
- [x] docker-compose.yml c лимитами под 4GB
- [x] .env.example
- [x] api/Dockerfile + requirements.txt (python:3.11-slim fastapi asyncpg)
- [x] bot/Dockerfile + requirements.txt
- [x] scripts/deploy_b2_medium.sh + backup.sh + check_grant.sh
- [x] MANIFEST.json

TASK_005 DONE -> TASK_006 (api скелет + endpoints)
