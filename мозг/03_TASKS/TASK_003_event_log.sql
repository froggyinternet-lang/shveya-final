-- TASK_003_event_log.sql — Event Log + Price Lock v1/v2 + Transfer immutable
-- CONSTITUTION Rule 3: Price Lock — цена только через snapshot, v1 не удаляется
-- CONSTITUTION Rule 5: Event Log + Transfer immutable — no UPDATE/DELETE
-- Budget <6.5K — DDL <100 строк

-- Part 1: Event Log + idempotency_key
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  garment_id UUID NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'state_change','courier_exception','photo_uploaded','payment_hold',
    'estimate_created','customer_agreed','customer_rejected','transfer_qr','return_confirmed'
  )),
  source_type TEXT NOT NULL CHECK (source_type IN ('operator','master','courier','system','customer','ai')),
  source_ref TEXT, -- id кнопки/исключения: btn_agree, exception_07, qr_scan_123
  idempotency_key VARCHAR(100) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT events_idempotency_global_unique UNIQUE (idempotency_key),
  CONSTRAINT events_garment_idempotency_unique UNIQUE (garment_id, idempotency_key),
  CONSTRAINT events_order_idempotency_unique UNIQUE (order_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_events_garment ON events(garment_id);
CREATE INDEX IF NOT EXISTS idx_events_order ON events(order_id);

-- Immutable Event Log
CREATE OR REPLACE RULE events_no_update AS ON UPDATE TO events DO INSTEAD NOTHING;
CREATE OR REPLACE RULE events_no_delete AS ON DELETE TO events DO INSTEAD NOTHING;

-- App-level idempotency: INSERT ... ON CONFLICT (idempotency_key) DO NOTHING — дубль не пишет
COMMENT ON COLUMN events.idempotency_key IS 'CONSTITUTION Rule 5: format {order_id}:{event_type}:{ts}:{rand6} — защита от дубля ЮKassa и двойного нажатия швеей, DO NOTHING при дубле';

-- Part 2: Price Lock EstimateVersion v1/v2
CREATE TABLE IF NOT EXISTS estimate_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  garment_id UUID NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  version_number INT NOT NULL CHECK (version_number >= 1),
  is_current BOOL NOT NULL DEFAULT true,
  price_snapshot JSONB NOT NULL, -- снимок price_versions на момент оценки
  total_price NUMERIC(10,2) NOT NULL,
  created_by UUID NOT NULL, -- operator_id NOT NULL — AI не допущен
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT estimate_garment_version_unique UNIQUE (garment_id, version_number)
);

-- Partial unique: только одна актуальная версия на garment
CREATE UNIQUE INDEX IF NOT EXISTS uniq_current_per_garment ON estimate_versions(garment_id) WHERE is_current = true;

-- v1 не удаляется — Rule 3 Price Lock
CREATE OR REPLACE RULE estimate_v1_no_delete AS ON DELETE TO estimate_versions WHERE OLD.version_number = 1 DO INSTEAD NOTHING;
CREATE OR REPLACE RULE estimate_versions_no_update AS ON UPDATE TO estimate_versions DO INSTEAD NOTHING;

COMMENT ON TABLE estimate_versions IS 'CONSTITUTION Rule 3: Price Lock — v1 immutable, is_current BOOL, payment_hold привязан к estimate_version_id';

-- Part 3: Transfer History immutable
CREATE TABLE IF NOT EXISTS transfer_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  garment_id UUID NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  from_owner TEXT NOT NULL CHECK (from_owner IN ('operator','master','courier','customer','storage')),
  to_owner TEXT NOT NULL CHECK (to_owner IN ('operator','master','courier','customer','storage')),
  item_number TEXT NOT NULL, -- TASK_011 проверка: не перепутана ли 7 — сканирование QR
  photo_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE RULE transfer_no_update AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
CREATE OR REPLACE RULE transfer_no_delete AS ON DELETE TO transfer_history DO INSTEAD NOTHING;

COMMENT ON TABLE transfer_history IS 'CONSTITUTION Rule 5: immutable — только INSERT, защита от потери цепочки владения';
