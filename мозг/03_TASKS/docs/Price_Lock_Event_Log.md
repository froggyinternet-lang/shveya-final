# Price_Lock + Event Log — Rule 3 + Rule 5

Источник: мозг/03_TASKS/TASK_003_price_lock.md и TASK_003_event_log.sql из 003 DONE

## Rule 3 — Price Lock (Заморозка цены)

**Проблема**: цена услуги может измениться после создания заказа.

**Решение SSOT**:
1. `price_versions` — версионирование. v1 не удаляется (триггер `trg_no_delete_v1`). Только одна `is_current=true` (partial unique index `ux_price_versions_current`).
2. При создании заказа:
   - `order_services.unit_price` копируется из `services.unit_price` на момент создания
   - `order_services.price_version_id` фиксирует версию прайса
   - `order_services.total_price` — GENERATED ALWAYS AS (quantity * unit_price) STORED
   - `orders.price_locked_at = now()`, `orders.total_price_locked = SUM(total_price)`
3. Последующие изменения `services.unit_price` не влияют на `order_services.unit_price` — цена заморожена.
4. Проверка в `003_constraints_check.sql`: `price_versions` v1 protected.

```sql
-- пример блокировки
UPDATE orders SET price_locked_at=now(), total_price_locked=(SELECT SUM(total_price) FROM order_services WHERE order_id=:id) WHERE id=:id;
```

## Rule 5 — Event Log (Неизменяемый журнал + idempotency)

**Проблема**: потеря порядка событий, дубли.

**Решение**:
1. `event_log` — append-only, `idempotency_key UNIQUE` (3/3).
   - Поля: order_id, event_type (ENUM 9 значений), payload JSONB, created_at
   - Index: (order_id, created_at)
2. `transfer_history` — immutable RULE:
   - Триггеры `trg_immutable_update/delete` кидают EXCEPTION при UPDATE/DELETE
   - Только INSERT разрешен
   - Хранит все переходы статусов, типы transfer_type ENUM 5 значений
3. `idempotency_registry` — общий реестр для доп. scope
4. Поток:
   - Клиент шлет запрос с `idempotency_key` → проверяем в `orders`/`payments`/`event_log` UNIQUE → если дубликат → возвращаем старый результат
   - Каждое действие пишет 2 строки: в `transfer_history` и `event_log`
   - `003_constraints_check.sql` проверяет 3 UNIQUE индекса

### Триграм-индекс
`gin_clients_name_trgm` на `clients.full_name` для поиска по фамилии — GIN + pg_trgm.

### pgcrypto
`gen_random_uuid()` для всех PK — обеспечивается `CREATE EXTENSION pgcrypto`.

### Итого RULE
- Rule 3 Price Lock: GENERATED total_price + price_version_id + price_locked_at + v1 protected
- Rule 5 Event Log: immutable transfer_history + event_log idempotency + pgcrypto + триграм

См. также ER_Diagram.md и 001_initial_final.sql.
