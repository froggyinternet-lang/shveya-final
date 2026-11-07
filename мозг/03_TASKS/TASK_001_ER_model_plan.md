# TASK_001 — ER-модель 20 сущностей которая не дает нарушить Конституцию
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_001
Дата: 2026-11-04
Бюджет: <6K токенов
Правило: вещь != заказ, цены только через версии, история передачи immutable

## 13 таблиц которые вшивают 7 правил Конституции в структуру

### Правило 1: Вещь != Заказ (Garment != Order)
```sql
-- orders — контейнер 1-10 вещей, БЕЗ QR
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL, -- NEW, ESTIMATED, AGREED, IN_WORK, READY, OUT_FOR_DELIVERY, DELIVERED, CLOSED
  zone VARCHAR(50), -- Мотовилиха и тд
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- items (garments) — вещь, QR только тут, UNIQUE NOT NULL
CREATE TABLE items (
  id UUID PRIMARY KEY,
  qr_code VARCHAR(32) UNIQUE NOT NULL, -- CONSTITUTION Rule 7: QR только к вещи
  order_id UUID, -- текущая привязка, но история через order_items
  sku VARCHAR(50), -- подшив, молния, шов
  declared_value INT, -- заявленная ценность
  completeness TEXT, -- что пришло: 1 брюки, 2 пуговицы и тд
  packaging_id VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- order_items — связь M:N, одна вещь может пройти через много заказов во времени (Wardrobe ID)
CREATE TABLE order_items (
  order_id UUID REFERENCES orders(id),
  item_id UUID REFERENCES items(id),
  PRIMARY KEY (order_id, item_id),
  added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Правило 2: Цены только через версии (не поменять без версии)
```sql
CREATE TABLE price_versions (
  id UUID PRIMARY KEY,
  version INT NOT NULL UNIQUE, -- v1, v2, снимок в каждом заказе
  valid_from TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE service_prices (
  id UUID PRIMARY KEY,
  price_version_id UUID REFERENCES price_versions(id) NOT NULL,
  sku VARCHAR(50) NOT NULL,
  zone VARCHAR(50) NOT NULL,
  price INT NOT NULL,
  UNIQUE(price_version_id, sku, zone)
);

CREATE TABLE estimates (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  price_version_id UUID REFERENCES price_versions(id) NOT NULL,
  price INT NOT NULL,
  status VARCHAR(20) NOT NULL -- ESTIMATED_V1, AGREED, REJECTED, ESTIMATED_V2
);
```

### Правило 3: История передачи immutable (не удалять)
```sql
CREATE TABLE transfer_history (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  from_entity VARCHAR(20) NOT NULL, -- CUSTOMER, COURIER, OPERATOR, MASTER, POINT
  to_entity VARCHAR(20) NOT NULL,
  qr_scanned VARCHAR(32) NOT NULL,
  photo_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 5: триггер запрещает UPDATE/DELETE
);

-- Триггер в DDL: CREATE RULE no_update AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
```

### Правило 4: Возврат обязателен чтобы закрыть заказ
```sql
CREATE TABLE return_confirmations (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id) NOT NULL UNIQUE,
  customer_confirmed BOOLEAN NOT NULL DEFAULT false,
  confirmed_at TIMESTAMPTZ,
  photo_url TEXT NOT NULL -- фото возврата
  -- CONSTITUTION Rule 4: без этого заказ не закрыть
);
```

### Правило 5: Результаты только с источником
```sql
CREATE TABLE results (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  source_type VARCHAR(20) NOT NULL, -- API, MANUAL, PHOTO
  source_ref TEXT NOT NULL, -- ссылка на документ/фото/API ответ + дата
  result_data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 1: без source_type + source_ref + created_at не сохранить
);
```

### Правило 6: Финансы только с operator_id (AI не допущен)
```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id) NOT NULL,
  amount INT NOT NULL,
  operator_id UUID NOT NULL, -- CONSTITUTION Rule 2: AI к фину не допущен, только оператор
  status VARCHAR(20) NOT NULL, -- HOLD_7D, CAPTURED, REFUNDED
  yookassa_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Правило 7: PostgreSQL единственный SSOT (дополнительно)
```sql
CREATE TABLE customers (id UUID PRIMARY KEY, phone_masked VARCHAR(20), consent BOOLEAN NOT NULL);
CREATE TABLE masters (id UUID PRIMARY KEY, name VARCHAR(100), zone VARCHAR(50));
CREATE TABLE couriers (id UUID PRIMARY KEY, name VARCHAR(100));
CREATE TABLE events (id UUID PRIMARY KEY, order_id UUID REFERENCES orders(id), idempotency_key VARCHAR(100) UNIQUE NOT NULL, event_type VARCHAR(50), payload JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
```

## Что делать в EXECUTOR_001

1. Прочитай DATA_COLLECTION_PROTOCOL_F0.12.md — фото 5 этапов привязка к Garment
2. Нарисуй ER-диаграмму mermaid (13 таблиц выше + связи)
3. Собери DDL v1 с триггерами и комментариями -- CONSTITUTION Rule N
4. Создай файл schema_v1_draft.sql <100 строк (один файл за раз через container:///)
5. Обнови KNOWLEDGE_GRAPH.md — добавь 13 таблиц и как они вшивают Конституцию
6. Создай TASK_001_done.md с summary

## Критерий готовности

- DDL не дает нарушить 7 правил даже если захочешь
- qr_code UNIQUE NOT NULL только в items
- transfer_history нельзя UPDATE/DELETE
- return_confirmations обязательна
- price только через price_versions
- payments требует operator_id

## Ограничения

- Зип не грузится — один файл за раз
- Бюджет <6.5K
- Не грузить весь V5 69KB, только раздел 5 и DATA Ф0.12
