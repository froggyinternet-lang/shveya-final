-- TASK_012 — 13 таблиц — Rule 7 наклейка рукой — критично — без hand_applied нельзя READY
-- Дата: 2026-11-05 — SHVEYA v2.4 — item_number UNIQUE PRM-YYYY-XXXX + order_number ORD-YYYYMMDD-XXX

-- 1. employees — 1 швея Пермь Мотовилиха — MVP — employee_id=1
CREATE TABLE IF NOT EXISTS employees (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL DEFAULT 'Швея Пермь 1 Мотовилиха',
  district TEXT NOT NULL DEFAULT 'Мотовилиха',
  max_orders_per_month INT NOT NULL DEFAULT 100,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO employees (id, name) VALUES (1, 'Швея Пермь 1 Мотовилиха') ON CONFLICT (id) DO NOTHING;

-- 2. clients — 152-ФЗ — ru-central1 — consent
CREATE TABLE IF NOT EXISTS clients (
  id SERIAL PRIMARY KEY,
  fio TEXT NOT NULL,
  phone TEXT NOT NULL,
  address TEXT NOT NULL,
  consent_152_fz BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. orders — order_number UNIQUE ORD-YYYYMMDD-XXX — для наклейки рукой — Яндекс Такси не путаются
CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  order_number TEXT NOT NULL UNIQUE CHECK (order_number ~ '^ORD-[0-9]{8}-[0-9]{3,}$'),
  client_id INT REFERENCES clients(id),
  status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW','ESTIMATED','AGREED','IN_WORK','READY','OUT_FOR_DELIVERY','DELIVERED','CLOSED','CANCELLED','DISPUTE')),
  declared_value INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. items — item_number UNIQUE PRM-YYYY-XXXX — Rule 7 — вещь с номером — наклейка рукой — qr_code_old для миграции TASK_011
CREATE TABLE IF NOT EXISTS items (
  id SERIAL PRIMARY KEY,
  item_number TEXT NOT NULL UNIQUE CHECK (item_number ~ '^PRM-[0-9]{4}-[0-9]{4,}$'),
  qr_code_old TEXT, -- deprecated — TASK_011 — QR -> номер — может быть NULL — QR зачеркнут
  order_id INT REFERENCES orders(id),
  name TEXT NOT NULL,
  defect TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS items_item_number_unique ON items(item_number);

-- 5. services
CREATE TABLE IF NOT EXISTS services (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  price INT NOT NULL
);

-- 6. order_item_services
CREATE TABLE IF NOT EXISTS order_item_services (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  item_id INT REFERENCES items(id),
  service_id INT REFERENCES services(id)
);

-- 7. photos — volume /app/photos — 5 фото — Rule 4 photo_url NOT NULL — локально volume, прод S3 ru-central1
CREATE TABLE IF NOT EXISTS photos (
  id SERIAL PRIMARY KEY,
  item_id INT REFERENCES items(id),
  photo_type TEXT NOT NULL CHECK (photo_type IN ('BEFORE','DEFECT','AFTER','STICKER_HANDWRITE','DELIVERY')),
  file_path TEXT NOT NULL, -- /app/photos/PRM-.../sticker_handwrite.jpg — C:\Perm_Repair\photos\PRM-...\sticker.jpg
  photo_url TEXT NOT NULL, -- Rule 4 — без фото нельзя READY
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. status_catalog
CREATE TABLE IF NOT EXISTS status_catalog (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL
);
INSERT INTO status_catalog (code, name) VALUES 
('NEW','Новый'),('ESTIMATED','Оценен'),('AGREED','Согласован'),('IN_WORK','В работе'),
('READY','Готов'),('OUT_FOR_DELIVERY','У курьера'),('DELIVERED','Доставлен'),('CLOSED','Закрыт'),
('CANCELLED','Отменен'),('DISPUTE','Спор')
ON CONFLICT (code) DO NOTHING;

-- 9. order_status_history
CREATE TABLE IF NOT EXISTS order_status_history (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  from_status TEXT,
  to_status TEXT NOT NULL,
  operator_id INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. stickers_log — Rule 7 [CRITICAL] — наклейка рукой — без hand_applied нельзя READY
CREATE TABLE IF NOT EXISTS stickers_log (
  id SERIAL PRIMARY KEY,
  item_id INT REFERENCES items(id),
  item_number TEXT NOT NULL, -- PRM-2026-0001 — UNIQUE — проверка перепутана 7
  order_number TEXT NOT NULL, -- ORD-2026-1105-001 — для наклейки
  fio TEXT NOT NULL, -- Иванов — для Яндекс Такси — фамилия на наклейке
  address TEXT NOT NULL, -- Пушкина 15-2 — для Яндекс Такси — адрес рукой — дубль с приложением
  item_name TEXT NOT NULL,
  is_hand_applied BOOLEAN NOT NULL DEFAULT true, -- Rule 7 — наклеена рукой — критично — без true нельзя READY
  applied_by INT NOT NULL DEFAULT 1 REFERENCES employees(id), -- Пермь 1 швея — employee_id=1
  photo_url TEXT NOT NULL, -- Rule 4 — фото наклейки обязательно — /app/photos/PRM-.../sticker_handwrite.jpg
  file_path TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Проверка Rule 7: без hand_applied нельзя READY
-- CREATE OR REPLACE FUNCTION check_sticker_hand_applied() ...

-- 11. payments — HOLD/CAPTURE/REFUND + operator_id NOT NULL Rule 2
CREATE TABLE IF NOT EXISTS payments (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  amount INT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('HOLD','CAPTURE','REFUND')),
  operator_id INT NOT NULL, -- Rule 2 — AI не допущен — только оператор
  idempotency_key TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. delivery_tasks — Яндекс Такси — только после READY — Rule 5 — адрес с наклейки рукой
CREATE TABLE IF NOT EXISTS delivery_tasks (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  item_number TEXT NOT NULL,
  address TEXT NOT NULL, -- с наклейки рукой — чтобы Яндекс Такси не путались — фамилия + адрес
  fio TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','IN_TRANSIT','DELIVERED','FAILED')),
  yandex_taxi_order_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. audit_log — 152-ФЗ — ru-central1 — audit + consent
CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  record_id INT NOT NULL,
  action TEXT NOT NULL,
  operator_id INT,
  data JSONB,
  region TEXT NOT NULL DEFAULT 'ru-central1',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7 правил в COMMENTS — SHVEYA v2.4
COMMENT ON TABLE items IS 'Rule 7: item_number PRM-YYYY-XXXX UNIQUE — вещь с номером — наклейка рукой — qr_code_old deprecated — TASK_011';
COMMENT ON TABLE stickers_log IS 'Rule 7 [CRITICAL]: is_hand_applied=true — наклеена рукой — без true нельзя READY — Яндекс Такси не путаются — фамилия + адрес рукой';
COMMENT ON TABLE orders IS 'Rule: order_number ORD-YYYYMMDD-XXX UNIQUE — для наклейки — швея пишет 001 — Яндекс Такси';
COMMENT ON TABLE photos IS 'Rule 4: photo_url NOT NULL — 5 фото — BEFORE/DEFECT/AFTER/STICKER_HANDWRITE/DELIVERY — volume /app/photos -> S3 ru-central1';
COMMENT ON TABLE employees IS 'Rule 4: 1 швея Пермь Мотовилиха — employee_id=1 — 100 заказов/мес — MVP';
COMMENT ON TABLE delivery_tasks IS 'Rule 5: Яндекс Такси только после READY — адрес с наклейки рукой — фамилия + адрес — дубль с приложением';
COMMENT ON TABLE audit_log IS 'Rule 6: 152-ФЗ — только ru-central1 — audit + consent — clients.consent_152_fz';
