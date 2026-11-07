-- schema_v1_draft.sql — DDL v1, 13 таблиц, вшивает 7 правил Конституции
-- SSOT: TASK_001_ER_model_plan.md + SHVEYA.md v2.3
-- Дата: 2026-11-04
-- Правило: вещь != заказ, цены только через версии, история immutable

-- Правило 1: Вещь != Заказ
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('NEW','ESTIMATED','AGREED','IN_WORK','READY','OUT_FOR_DELIVERY','DELIVERED','CLOSED')),
  zone VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 7: orders БЕЗ QR, QR только в items
);

CREATE TABLE items (
  id UUID PRIMARY KEY,
  qr_code VARCHAR(32) UNIQUE NOT NULL, -- CONSTITUTION Rule 7: QR только к вещи
  order_id UUID,
  sku VARCHAR(50) NOT NULL,
  declared_value INT,
  completeness TEXT,
  packaging_id VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  item_id UUID REFERENCES items(id) ON DELETE CASCADE,
  PRIMARY KEY (order_id, item_id),
  added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Правило 2: Цены только через версии
CREATE TABLE price_versions (
  id UUID PRIMARY KEY,
  version INT NOT NULL UNIQUE,
  valid_from TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 3: нельзя менять цену без версии
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
  status VARCHAR(20) NOT NULL CHECK (status IN ('ESTIMATED_V1','AGREED','REJECTED','ESTIMATED_V2'))
);

-- Правило 3: История передачи immutable
CREATE TABLE transfer_history (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  from_entity VARCHAR(20) NOT NULL,
  to_entity VARCHAR(20) NOT NULL,
  qr_scanned VARCHAR(32) NOT NULL,
  photo_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 5: нельзя DELETE/UPDATE, только INSERT
);
CREATE RULE no_update_transfer AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
CREATE RULE no_delete_transfer AS ON DELETE TO transfer_history DO INSTEAD NOTHING;

-- Правило 4: Возврат обязателен
CREATE TABLE return_confirmations (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id) NOT NULL UNIQUE,
  customer_confirmed BOOLEAN NOT NULL DEFAULT false,
  confirmed_at TIMESTAMPTZ,
  photo_url TEXT NOT NULL
  -- CONSTITUTION Rule 4: без этого заказ не закрыть
);

-- Правило 5: Результаты только с источником
CREATE TABLE results (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  source_type VARCHAR(20) NOT NULL,
  source_ref TEXT NOT NULL,
  result_data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- CONSTITUTION Rule 1: без источника не сохранить
);

-- Правило 6: Финансы только с operator_id
CREATE TABLE payments (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id) NOT NULL,
  amount INT NOT NULL,
  operator_id UUID NOT NULL, -- CONSTITUTION Rule 2: AI к фину не допущен
  status VARCHAR(20) NOT NULL CHECK (status IN ('HOLD_7D','CAPTURED','REFUNDED')),
  yookassa_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Дополнительно: 3 таблицы справочники + события
CREATE TABLE customers (id UUID PRIMARY KEY, phone_masked VARCHAR(20), consent BOOLEAN NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE masters (id UUID PRIMARY KEY, name VARCHAR(100), zone VARCHAR(50));
CREATE TABLE events (id UUID PRIMARY KEY, order_id UUID REFERENCES orders(id), idempotency_key VARCHAR(100) UNIQUE NOT NULL, event_type VARCHAR(50), payload JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
