-- ============================================================
-- TASK_004 — 001_initial_final.sql — b2.medium PostgreSQL SSOT
-- 20 таблиц, 10 ENUM, pgcrypto, pg_trgm, все RULE из ТЗ
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ==================== 10 ENUM СТАТУСОВ ====================
CREATE TYPE client_status_enum AS ENUM ('NEW','ACTIVE','BLOCKED');
CREATE TYPE order_status_enum AS ENUM ('NEW','ACCEPTED','PICKUP_SCHEDULED','PICKED_UP','IN_WORK','READY','OUT_FOR_DELIVERY','DELIVERED','CANCELLED','RETURNED');
CREATE TYPE garment_status_enum AS ENUM ('RECEIVED','DIAGNOSIS','IN_REPAIR','QC','READY','ISSUED');
CREATE TYPE leg_status_enum AS ENUM ('PENDING','ASSIGNED','IN_TRANSIT','DELIVERED','FAILED');
CREATE TYPE payment_status_enum AS ENUM ('PENDING','LOCKED','CAPTURED','REFUNDED','FAILED');
CREATE TYPE courier_status_enum AS ENUM ('AVAILABLE','BUSY','OFFLINE','BLOCKED');
CREATE TYPE point_status_enum AS ENUM ('OPEN','CLOSED','TEMP_CLOSED');
CREATE TYPE transfer_type_enum AS ENUM ('ORDER_CREATE','STATUS_CHANGE','PAYMENT','COURIER_ASSIGN','PRICE_LOCK');
CREATE TYPE event_type_enum AS ENUM ('ORDER_CREATED','LEG_CREATED','GARMENT_ADDED','STATUS_CHANGED','PRICE_LOCKED','PAYMENT_LOCKED','COURIER_ASSIGNED','EXCEPTION','DELIVERED');
CREATE TYPE exception_code_enum AS ENUM ('CLIENT_NO_SHOW','ADDRESS_WRONG','CLIENT_REFUSED','DAMAGE','LOST','DELAY','WEATHER','ROAD_CLOSED','VEHICLE_BREAK','OVERLOAD','WRONG_POINT','DOOR_CLOSED','PHONE_OFF','OTHER','RETRY');

-- ==================== ТАБЛИЦЫ 1-7 СПРАВОЧНИКИ ====================

-- 1. clients
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone VARCHAR(20) NOT NULL,
  full_name TEXT NOT NULL,
  status client_status_enum NOT NULL DEFAULT 'NEW',
  idempotency_key TEXT, -- будет уникальный через partial? Но по ТЗ 3 таблицы, здесь не считаем
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_clients_phone ON clients(phone);
CREATE INDEX gin_clients_name_trgm ON clients USING GIN (full_name gin_trgm_ops); -- триграм-индекс

-- 2. client_addresses
CREATE TABLE client_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  address_text TEXT NOT NULL,
  zone_id UUID,
  is_current BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- partial unique is_current
CREATE UNIQUE INDEX ux_client_addresses_current ON client_addresses(client_id) WHERE is_current = true;

-- 3. garment_types (seed 6)
CREATE TABLE garment_types (
  id SMALLINT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

-- 4. measurements (seed 6)
CREATE TABLE measurements (
  id SMALLINT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT 'cm'
);

-- 5. zones (Мотовилиха и др)
CREATE TABLE zones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  city TEXT NOT NULL DEFAULT 'Пермь',
  is_active BOOLEAN NOT NULL DEFAULT true
);

-- 6. shveya_points (2 точки)
CREATE TABLE shveya_points (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  zone_id UUID NOT NULL REFERENCES zones(id),
  address TEXT NOT NULL,
  status point_status_enum NOT NULL DEFAULT 'OPEN',
  is_current BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX ux_shveya_points_current ON shveya_points(code) WHERE is_current = true;

-- 7. couriers
CREATE TABLE couriers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL,
  phone VARCHAR(20) NOT NULL UNIQUE,
  status courier_status_enum NOT NULL DEFAULT 'AVAILABLE',
  current_zone_id UUID REFERENCES zones(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================== 8-14 CORE ====================

-- 8. orders — центральная
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id),
  status order_status_enum NOT NULL DEFAULT 'NEW',
  zone_id UUID REFERENCES zones(id),
  point_id UUID REFERENCES shveya_points(id),
  idempotency_key TEXT NOT NULL,
  price_locked_at TIMESTAMPTZ,
  total_price_locked NUMERIC(10,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_orders_idempotency ON orders(idempotency_key);

-- 9. order_legs — плечи доставки, CHECK leg_number IN (1,2)
CREATE TABLE order_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  leg_number SMALLINT NOT NULL CHECK (leg_number IN (1,2)),
  status leg_status_enum NOT NULL DEFAULT 'PENDING',
  courier_id UUID REFERENCES couriers(id),
  from_point_id UUID REFERENCES shveya_points(id),
  to_address_id UUID REFERENCES client_addresses(id),
  scheduled_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_order_leg UNIQUE (order_id, leg_number)
);

-- 10. garments — изделия в заказе
CREATE TABLE garments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  garment_type_id SMALLINT NOT NULL REFERENCES garment_types(id),
  status garment_status_enum NOT NULL DEFAULT 'RECEIVED',
  defect_text TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 11. garment_measurements
CREATE TABLE garment_measurements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  garment_id UUID NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  measurement_id SMALLINT NOT NULL REFERENCES measurements(id),
  value_num NUMERIC(6,2) NOT NULL,
  is_current BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_garment_meas_current ON garment_measurements(garment_id, measurement_id) WHERE is_current = true;

-- 12. price_versions — версионирование прайса, v1 не удаляется
CREATE TABLE price_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version_code TEXT NOT NULL UNIQUE, -- v1, v2 ...
  is_current BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_price_versions_current ON price_versions(is_current) WHERE is_current = true;

-- 13. services — прайс-лист
CREATE TABLE services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  garment_type_id SMALLINT REFERENCES garment_types(id),
  price_version_id UUID NOT NULL REFERENCES price_versions(id),
  unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
  is_active BOOLEAN NOT NULL DEFAULT true,
  UNIQUE(code, price_version_id)
);

-- 14. order_services — GENERATED total_price
CREATE TABLE order_services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  garment_id UUID NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  service_id UUID NOT NULL REFERENCES services(id),
  quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
  unit_price NUMERIC(10,2) NOT NULL,
  total_price NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
  price_version_id UUID NOT NULL REFERENCES price_versions(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================== 15-20 PAYMENT / LOG / STATE ====================

-- 15. payments
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
  status payment_status_enum NOT NULL DEFAULT 'PENDING',
  idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_payments_idempotency ON payments(idempotency_key);

-- 16. transfer_history — immutable RULE
CREATE TABLE transfer_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  leg_id UUID REFERENCES order_legs(id),
  transfer_type transfer_type_enum NOT NULL,
  from_status TEXT,
  to_status TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 17. event_log — из TASK_003-1
CREATE TABLE event_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  event_type event_type_enum NOT NULL,
  payload JSONB NOT NULL,
  idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_event_log_idempotency ON event_log(idempotency_key);
CREATE INDEX ix_event_log_order ON event_log(order_id, created_at);

-- 18. state_transitions — 13 переходов
CREATE TABLE state_transitions (
  id SMALLINT PRIMARY KEY,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  entity TEXT NOT NULL, -- ORDER / GARMENT
  is_allowed BOOLEAN NOT NULL DEFAULT true,
  UNIQUE(from_status, to_status, entity)
);

-- 19. courier_exceptions — 14 кодов
CREATE TABLE courier_exceptions (
  id SMALLINT PRIMARY KEY,
  code exception_code_enum NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  is_retryable BOOLEAN NOT NULL DEFAULT true
);

-- 20. idempotency_registry — доп. контроль идемпотентности (опционально)
CREATE TABLE idempotency_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  scope TEXT NOT NULL, -- orders/payments/events
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================== RULES / TRIGGERS ====================

-- RULE: price_versions v1 не удаляется
CREATE OR REPLACE FUNCTION fn_prevent_v1_delete() RETURNS TRIGGER AS $$
BEGIN
  IF OLD.version_code = 'v1' THEN
    RAISE EXCEPTION 'RULE v1 не удаляется: price_versions v1 protected';
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_no_delete_v1
BEFORE DELETE ON price_versions
FOR EACH ROW EXECUTE FUNCTION fn_prevent_v1_delete();

-- RULE: transfer_history immutable (no UPDATE, no DELETE)
CREATE OR REPLACE FUNCTION fn_immutable_transfer_history() RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'RULE immutable transfer_history: UPDATE/DELETE forbidden';
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_immutable_update
BEFORE UPDATE ON transfer_history
FOR EACH ROW EXECUTE FUNCTION fn_immutable_transfer_history();

CREATE TRIGGER trg_immutable_delete
BEFORE DELETE ON transfer_history
FOR EACH ROW EXECUTE FUNCTION fn_immutable_transfer_history();

-- updated_at триггер для orders, clients
CREATE OR REPLACE FUNCTION fn_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_orders_touch BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();
CREATE TRIGGER trg_clients_touch BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

-- FK zones для client_addresses (добавляем после создания zones)
ALTER TABLE client_addresses ADD CONSTRAINT fk_client_addr_zone FOREIGN KEY (zone_id) REFERENCES zones(id);

-- Комментарии
COMMENT ON TABLE order_legs IS 'CHECK leg_number IN (1,2) + UNIQUE(order_id, leg_number)';
COMMENT ON TABLE price_versions IS 'partial unique is_current WHERE is_current + RULE v1 не удаляется';
COMMENT ON TABLE transfer_history IS 'RULE immutable';
COMMENT ON COLUMN orders.idempotency_key IS 'UNIQUE 1/3';
COMMENT ON COLUMN payments.idempotency_key IS 'UNIQUE 2/3';
COMMENT ON COLUMN event_log.idempotency_key IS 'UNIQUE 3/3';
