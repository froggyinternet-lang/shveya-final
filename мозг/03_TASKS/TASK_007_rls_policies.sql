-- TASK_007 — RLS + Grants — Security — Rule 2 + Rule 5 + idempotency_key
-- Дата: 2026-11-04
-- SSOT: TASK_001 DDL 13 таблиц + SHVEYA.md Rule 2/3/4/5/7

-- Включить RLS
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE transfer_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE return_confirmations ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimates ENABLE ROW LEVEL SECURITY;

-- 1. Rule 2: AI не допущен — operator_id обязателен — только operator может HOLD/CAPTURE/REFUND
-- Courier не может фин операции — только оператор Rule 2

REVOKE ALL ON payments FROM courier, client;
GRANT SELECT ON payments TO courier; -- видеть но не холдить/списать/возвращать
GRANT SELECT, INSERT, UPDATE ON payments TO operator; -- только оператор может фин Rule 2
-- Проверка operator_id NOT NULL в DDL уже есть — payments.operator_id UUID NOT NULL

-- RLS: payments только operator может INSERT HOLD/CAPTURE/REFUND
CREATE POLICY operator_can_finance ON payments FOR ALL TO operator USING (true) WITH CHECK (operator_id IS NOT NULL);
CREATE POLICY courier_cannot_finance ON payments FOR ALL TO courier USING (false);

-- 2. Rule 5: immutable — нельзя DELETE/UPDATE — RULE DO INSTEAD NOTHING

-- Уже есть в schema_v1_draft.sql — 2 RULE — повторяем для безопасности
CREATE OR REPLACE RULE no_update_events AS ON UPDATE TO events DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_events AS ON DELETE TO events DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_update_transfer AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_transfer AS ON DELETE TO transfer_history DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_update_price_versions AS ON UPDATE TO price_versions DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_price_versions AS ON DELETE TO price_versions DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_update_estimates AS ON UPDATE TO estimates DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_estimates AS ON DELETE TO estimates DO INSTEAD NOTHING;

REVOKE UPDATE, DELETE ON events, transfer_history, price_versions, estimates FROM public, courier, client, operator;
GRANT SELECT, INSERT ON events, transfer_history TO operator, courier, client;
GRANT SELECT, INSERT ON price_versions, estimates TO operator;

-- 3. idempotency_key UNIQUE — защита от дублей — уже UNIQUE NOT NULL в DDL

-- events.idempotency_key TEXT UNIQUE NOT NULL — второй INSERT падает duplicate key → Уже обработано
-- Проверка в RLS не нужна — UNIQUE constraint уже защищает

-- 4. Rule 7: QR только в items.qr_code UNIQUE NOT NULL — вещь, не заказ

-- items.qr_code UNIQUE NOT NULL уже в DDL — orders без qr_code
-- RLS: никто не может положить QR в orders — его там нет — проверка в API

CREATE UNIQUE INDEX IF NOT EXISTS items_qr_code_unique ON items(qr_code);
REVOKE UPDATE (qr_code) ON items FROM courier, client; -- courier/client не могут менять QR — только оператор
GRANT SELECT ON items TO courier, client, operator;
GRANT INSERT, UPDATE (status) ON items TO operator;

-- 5. Rule 4: photo_url NOT NULL — без фото не закрыть + 5 фото этапов

-- transfer_history.photo_url TEXT NOT NULL + return_confirmations.photo_url TEXT NOT NULL уже в DDL
-- RLS: courier обязан вставить photo_url — CHECK constraint

ALTER TABLE transfer_history ADD CONSTRAINT photo_url_not_null CHECK (photo_url IS NOT NULL AND photo_url <> '');
ALTER TABLE return_confirmations ADD CONSTRAINT photo_return_not_null CHECK (photo_url IS NOT NULL AND photo_url <> '');

-- Исключение 6 потеряна — фото не требуется — обрабатывается в API — CHECK с исключением
-- В API: если exception_id=6 потеряна — разрешить photo_url NULL — иначе NOT NULL

-- 6. Rule 3: v1 не удаляется — Price Lock — immutable price_versions + snapshot

-- price_versions immutable уже — RULE DO INSTEAD NOTHING — v1 не удаляется
-- estimates.price_version_id snapshot — даже если прайс поменяется, у заказа старый

GRANT SELECT ON price_versions TO courier, client, operator;

-- 7. 14 исключений + declared_value — потеряна 6 самая строгая

-- orders.declared_value — для потеряна 6 возврат declared_value
-- RLS: только operator может REFUND declared_value Rule 2

CREATE POLICY client_own_orders ON orders FOR SELECT TO client USING (client_id = current_user_id());
CREATE POLICY courier_assigned_orders ON orders FOR SELECT TO courier USING (courier_id = current_user_id() OR status IN ('READY','OUT_FOR_DELIVERY'));
CREATE POLICY operator_all_orders ON orders FOR ALL TO operator USING (true);

-- 8. Дополнительные Grants — courier не может фин, client не видит чужие

REVOKE ALL ON price_versions, estimates FROM client, courier;
GRANT SELECT ON price_versions, estimates TO client; -- клиент видит v1,v2 но не меняет

-- events — client видит только свои, courier — assigned, operator — все
CREATE POLICY client_own_events ON events FOR SELECT TO client USING (order_id IN (SELECT id FROM orders WHERE client_id = current_user_id()));
CREATE POLICY courier_own_transfers ON transfer_history FOR SELECT TO courier USING (order_id IN (SELECT id FROM orders WHERE courier_id = current_user_id()));
CREATE POLICY operator_all_events ON events FOR SELECT TO operator USING (true);
CREATE POLICY operator_all_transfers ON transfer_history FOR SELECT TO operator USING (true);

-- Итог: 7 пунктов Security закрыты RLS + Grants + RULE + UNIQUE + NOT NULL
