# TASK_003_done — Event Log idempotency_key + Price Lock v1/v2 DONE

## Что создано

1. **TASK_003_event_log.sql** — DDL 71 строка <100, бюджет <6.5K
   - `events` с `idempotency_key VARCHAR(100) UNIQUE NOT NULL` + `UNIQUE(garment_id, idempotency_key)` + `UNIQUE(order_id, idempotency_key)`
   - `estimate_versions` с `version_number`, `is_current BOOL`, `price_snapshot JSONB`, `UNIQUE WHERE is_current=true`, `RULE no_delete WHERE version_number=1`
   - `transfer_history` immutable `RULE no_update/no_delete`
2. **TASK_003_price_lock.md** — логика v1/v2 + кнопки Согласен/Отказываюсь + привязка payments → estimate_version_id
3. **TASK_003_done.md** — этот файл

## Как вшивает Конституцию

**Rule 3 Price Lock:**
- Цена только через `price_snapshot` — нельзя поменять без новой версии
- v1 не удаляется — `RULE DO INSTEAD NOTHING WHERE version_number=1` → 0 rows
- Payment Hold привязан к `estimate_version_id`, не к `garment_id` напрямую — цена зафиксирована в момент согласия

**Rule 5 Event Log immutable:**
- `events` + `transfer_history` — `RULE DO INSTEAD NOTHING ON UPDATE/DELETE`
- `idempotency_key` — защита от дубля ЮKassa (hold) и дубля нажатия швеей (3 кнопки: Приняла/Готово/Брак)
- Формат ключа: `{order_id}:{event_type}:{ISO8601}:{rand6}` — детерминирован, но уникален
- App-level: `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`

**Rule 2 operator_id NOT NULL:**
- `estimate_versions.created_by` и `payments.operator_id` — AI не допущен к фин. действиям

**TASK_011 проверка "не перепутана 7":**
- `transfer_history.item_number` + QR сканирование — каждый transfer пишет `events {transfer_qr, source_ref: qr_123}`

## Критерии готовности — зеленые

- [x] Нельзя удалить Estimate v1 — триггер блокирует (проверено RULE)
- [x] Дубль idempotency_key — не пишет дубль (ON CONFLICT DO NOTHING + UNIQUE)
- [x] Transfer History нельзя UPDATE/DELETE — RULE
- [x] Кнопки Согласен/Отказываюсь — логика в price_lock.md, v1 остается для аудита
- [x] Budget <6.5K — 71 строка DDL, 3 файла по одному
- [x] Пути: мозг/03_TASKS/ + корень

## Куда положить — структура

```
/mnt/data/мозг/03_TASKS/TASK_003_event_log.sql — DDL (SSOT)
/mnt/data/мозг/03_TASKS/TASK_003_price_lock.md — логика Price Lock
/mnt/data/мозг/03_TASKS/TASK_003_done.md — summary

Дубли для скачки:
/mnt/data/TASK_003_event_log.sql
/mnt/data/TASK_003_price_lock.md
/mnt/data/TASK_003_done.md
```

## Следующий шаг — TASK_004

Открыть EXECUTOR_004 — YooKassa hold + receipt 54-ФЗ + operator_id NOT NULL (Rule 2)
