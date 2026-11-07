# TASK_003 Price Lock — EstimateVersion v1/v2

## CONSTITUTION Rule 3: Цена только через snapshot

**Проблема:** оператор меняет прайс после оценки → клиент видит другую цену.

**Решение:** Price Lock через `estimate_versions.price_snapshot JSONB` + `total_price`

### Таблица estimate_versions

```
id UUID PK
garment_id FK → garments(id)
version_number INT 1,2...
is_current BOOL — только одна true на garment (partial unique index)
price_snapshot JSONB — снимок {service_id, price_version_id, qty, unit_price} на момент оценки
total_price NUMERIC(10,2)
created_by UUID NOT NULL — operator_id, AI не допущен (Rule 2)
created_at TIMESTAMPTZ
UNIQUE(garment_id, version_number)
UNIQUE INDEX (garment_id) WHERE is_current=true
```

### Защита v1

```sql
-- v1 не удаляется никогда
CREATE RULE estimate_v1_no_delete AS ON DELETE TO estimate_versions 
WHERE OLD.version_number = 1 DO INSTEAD NOTHING;

-- Price Lock immutable — нельзя UPDATE
CREATE RULE estimate_versions_no_update AS ON UPDATE TO estimate_versions 
DO INSTEAD NOTHING;
```

Попытка `DELETE WHERE version_number=1` → `0 rows deleted` — триггер блокирует.

### Логика v1/v2

1. **NEW→ESTIMATED:** оператор создает `estimate_versions v1` — `is_current=true`, `price_snapshot` = снимок из `price_versions` + `service_prices UNIQUE`
2. **ESTIMATED:** клиент видит v1 + фото 5 этапов (TASK_002)
3. **Кнопки клиента:**
   - **Согласен** → `events {event_type: customer.agreed, source_ref: btn_agree, idempotency_key: order_id:agreed:ts:rand}` → `estimate_versions v1` остается `is_current=true` → State `AGREED` → `payments` создается с `estimate_version_id = v1.id`
   - **Отказываюсь** → `events {event_type: customer.rejected, source_ref: btn_reject}` → создается `DISPUTE` статус (Rule 4) → v1 НЕ удаляется, остается для аудита → оператор может создать v2 (новая оценка) → `v1.is_current=false`, `v2.is_current=true` (partial unique переключает)

### Связь с payments — Price Lock

```
payments.estimate_version_id FK → estimate_versions(id) NOT NULL
payments.operator_id NOT NULL
payments.yookassa_hold_id — hold привязан к зафиксированной цене v1/v2
```

Цена зафиксирована в момент `customer.agreed` — даже если `service_prices` поменяется завтра, `payments.total` берет из `estimate_versions.price_snapshot`, а не из живого прайса.

### Idempotency для кнопок

Клиент жмет Согласен 2 раза → `idempotency_key = order_id:customer.agreed:20261105T120000Z:abc123` → второй INSERT → `ON CONFLICT (idempotency_key) DO NOTHING` → дубль не пишет, платеж не дублируется.

То же для швеи: нажала Готово 2 раза → `garment_id:transfer_qr:ts:rand` → второй игнорируется.

### Что защищает

- Нельзя удалить Estimate v1 — RULE блокирует
- Дубль idempotency_key — DO NOTHING
- Transfer History нельзя UPDATE/DELETE — только INSERT
- AI не создает estimate — created_by operator_id NOT NULL
