# CONTEXT — текущий фокус
Дата: 2026-11-05 05:40 AM
Ветка: PLANNER — TASK_003-1 DONE

✅ 000 ЧИСТКА DONE
✅ 001 ER-модель 20 сущностей DONE
✅ 002 State Machine 8 шагов + 14 исключений + миграции DONE
🔄 003 Event Log + Price Lock — Файл 1/3 DONE

Что сделано в 003-1:
- events: idempotency_key VARCHAR(100) UNIQUE NOT NULL формат {order_id}:{event_type}:{ts}:{rand6}, UNIQUE(garment_id, idempotency_key) + UNIQUE(order_id, idempotency_key) + UNIQUE(idempotency_key), event_type 9 типов, source_type 6 типов + source_ref, RULE DO INSTEAD NOTHING на UPDATE/DELETE + ON CONFLICT DO NOTHING — дубль ЮKassa и двойное нажатие швеей не пишет дубль — Rule 5
- estimate_versions: version_number INT, is_current BOOL, price_snapshot JSONB, total_price, created_by operator_id NOT NULL Rule 2, UNIQUE(garment_id, version_number) + UNIQUE INDEX WHERE is_current=true — только одна актуальная, RULE WHERE OLD.version_number=1 DO INSTEAD NOTHING — v1 не удаляется никогда, RULE no_update — Price Lock не меняется после фиксации — Rule 3
- transfer_history: from_owner/to_owner, item_number проверка TASK_011 не перепутана 7, RULE no_update/no_delete — только INSERT, цепочка владения не теряется
- 71 строка, бюджет <6.5K

Следующее: 003-2 — TASK_003_price_lock.md — логика кнопок Согласен/Отказываюсь + привязка payment_hold → estimate_version_id
Ветка: EXECUTOR_003

После 003-2 → 003-3 TASK_003_done.md → 004 DDL финальный для b2.medium
