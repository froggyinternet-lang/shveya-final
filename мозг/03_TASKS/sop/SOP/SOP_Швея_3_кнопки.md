# SOP_Швея_3_кнопки — Приняла / Готово / Брак

**Версия:** v1.0 TASK_006 | State_Machine.md из 004 | events.idempotency_key UNIQUE

### Цель
Один экран, 3 большие кнопки. Любое нажатие — неизменяемый след + защита от дубля.

### UI
Экран швеи: вверху QR PRM-2026-0001 + фото front + дефект.
3 кнопки:
1. 🟢 [ПРИНЯЛА В РАБОТУ] 
2. 🔵 [ГОТОВО]
3. 🔴 [БРАК]

Только одна активна в зависимости от статуса.

### State Machine (из 004)
ПРИЕМКА → (Приняла) → В_РАБОТЕ → (Готово) → ГОТОВО → ВЫДАЧА
В_РАБОТЕ → (Брак) → БРАК → ПРИЕМКА (переприемка)

### Кнопка 1: Приняла
- Условие: статус = ПРИЕМКА, QR отсканирован швеей
- Действие:
```sql
INSERT INTO transfer_history (item_id, from_stage, to_stage, actor, meta)
VALUES (<id>, 'ПРИЕМКА', 'В_РАБОТЕ', 'shveya_anna', '{"action":"accepted"}');

INSERT INTO events (id, item_id, type, idempotency_key, payload)
VALUES (gen_random_uuid(), <id>, 'SEAMSTRESS_ACCEPTED', 'PRM-2026-0001:ACCEPTED:<timestamp>', '{"by":"shveya_anna"}')
ON CONFLICT (idempotency_key) DO NOTHING; -- защита от дубля
```
- transfer_history immutable — только INSERT, никаких UPDATE.
- events.idempotency_key UNIQUE — формат: {item_number}:{ACTION}:{YYYYMMDDHHmm} или uuid. Повторный клик не создает дубль.

### Кнопка 2: Готово
- Условие: статус = В_РАБОТЕ
- Обязательные поля перед кликом: что сделано (текст), время работы.
- Действие:
```sql
INSERT INTO transfer_history (item_id, from_stage, to_stage, actor) 
VALUES (<id>, 'В_РАБОТЕ', 'ГОТОВО', 'shveya_anna');

INSERT INTO events (item_id, type, idempotency_key) 
VALUES (<id>, 'SEAMSTRESS_DONE', 'PRM-2026-0001:DONE:<uuid>');
```
- Фото результата опционально но рекомендуется в artifacts type='after'.

### Кнопка 3: Брак
- Условие: любой момент в В_РАБОТЕ
- Обязательно: фото брака + причина (enum: ткань_поползла, фурнитура_нет, пятно_не_ушло, клиентский_брак)
- Действие:
```sql
INSERT INTO transfer_history (item_id, from_stage, to_stage, actor, meta)
VALUES (<id>, 'В_РАБОТЕ', 'БРАК', 'shveya_anna', '{"reason":"..."}');

INSERT INTO events (item_id, type, idempotency_key, payload)
VALUES (<id>, 'SEAMSTRESS_DEFECT', 'PRM-2026-0001:DEFECT:<uuid>', '{"reason":"..."}');
```

### Idempotency — КРИТИЧНО
- Фронт генерит idempotency_key до отправки.
- Бэк: UNIQUE constraint. Если дубль — возвращает 200 OK но не пишет повторно.
- Логика: швея может жать 2 раза из-за лага — система не должна задвоить transfer_history.

### Логика неизменяемости
- transfer_history: REVOKE UPDATE, DELETE для роли shveya.
- Только INSERT + SELECT.
- Аудит через created_at.

### DoD для каждой кнопки
- [ ] QR отсканирован
- [ ] Кнопка нажата 1 раз
- [ ] transfer_history запись появилась
- [ ] events запись с UNIQUE idempotency_key
- [ ] Статус в items обновлен (триггером от transfer_history, не напрямую)
