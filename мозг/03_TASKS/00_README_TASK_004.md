# TASK_004 — Куда разложить

ZIP создан веткой EXECUTOR_004 (b2.medium PostgreSQL SSOT).

## Извлечение
1. Скачай TASK_004_ALL.zip
2. ПКМ → Извлечь все → `C:\Perm_Repair\`
3. Итоговый путь должен быть `C:\Perm_Repair\мозг\03_TASKS\...`

## Куда копировать (SSOT)

Из папки `TASK_004_ALL/` разложи так:

```
C:\Perm_Repair\мозг\03_TASKS\
├── migrations\
│   ├── 001_initial_final.sql  ← из DDL/001_initial_final.sql (финальный DDL 20 таблиц)
│   ├── 002_seed.sql           ← из DDL/002_seed.sql
│   └── 003_constraints_check.sql ← из DDL/003_constraints_check.sql
└── docs\
    ├── ER_Diagram.md          ← из DOCS/ER_Diagram.md
    ├── State_Machine.md       ← из DOCS/State_Machine.md
    └── Price_Lock_Event_Log.md← из DOCS/Price_Lock_Event_Log.md
```

## Порядок применения на b2.medium
1. `psql -f migrations/001_initial_final.sql`
2. `psql -f migrations/002_seed.sql`
3. `psql -f migrations/003_constraints_check.sql` — должен вывести OK по всем RULE

## Что внутри DDL
- 20 таблиц, pgcrypto + pg_trgm
- 10 ENUM статусов
- CHECK leg_number IN (1,2)
- UNIQUE(order_id, leg_number)
- Partial UNIQUE is_current WHERE is_current = true
- RULE v1 не удаляется (trigger)
- RULE immutable transfer_history
- 3x UNIQUE idempotency_key (orders, payments, event_log)
- GENERATED total_price
- Триграм GIN индекс по clients

Ветка: EXECUTOR_004 / PLANNER vs EXECUTOR rule соблюдено — один ZIP, без доп. вкладок.
Бюджет <6.5K.
