-- schema_migration_qr_to_number.sql — Шаг 2 DONE — 2026-11-05
-- Миграция QR → item_number + order_number

-- Sequence для item_number PRM-2026-0001
CREATE SEQUENCE IF NOT EXISTS item_number_seq START 1;
CREATE OR REPLACE FUNCTION generate_item_number() RETURNS VARCHAR AS $$
  SELECT 'PRM-' || to_char(now(),'YYYY') || '-' || lpad(nextval('item_number_seq')::text, 4, '0');
$$ LANGUAGE sql;

-- Sequence для order_number ORD-2026-0001
CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1;
CREATE OR REPLACE FUNCTION generate_order_number() RETURNS VARCHAR AS $$
  SELECT 'ORD-' || to_char(now(),'YYYY') || '-' || lpad(nextval('order_number_seq')::text, 4, '0');
$$ LANGUAGE sql;

-- 1. Добавляем item_number в items, мигрируем старые qr_code
ALTER TABLE items ADD COLUMN IF NOT EXISTS item_number VARCHAR(20);
UPDATE items SET item_number = qr_code WHERE item_number IS NULL AND qr_code IS NOT NULL;
-- Для тех у кого нет qr_code — генерим
UPDATE items SET item_number = generate_item_number() WHERE item_number IS NULL;

ALTER TABLE items ALTER COLUMN item_number SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS items_item_number_unique ON items(item_number);

-- 2. Делаем qr_code NULLABLE + partial unique
ALTER TABLE items ALTER COLUMN qr_code DROP NOT NULL;
DROP INDEX IF EXISTS items_qr_code_unique;
CREATE UNIQUE INDEX IF NOT EXISTS items_qr_code_partial_unique ON items(qr_code) WHERE qr_code IS NOT NULL;

-- 3. Добавляем order_number в orders
ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_number VARCHAR(20);
UPDATE orders SET order_number = generate_order_number() WHERE order_number IS NULL;
ALTER TABLE orders ALTER COLUMN order_number SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS orders_order_number_unique ON orders(order_number);

-- 4. Добавляем item_number в transfer_history для проверки при выдаче
ALTER TABLE transfer_history ADD COLUMN IF NOT EXISTS item_number VARCHAR(20);
-- Проверка: при выдаче сверяем transfer_history.item_number = items.item_number — ловит перепутана 7

-- Комментарий: фото наклейки + вещи обязательно в Photo 1 Приём
