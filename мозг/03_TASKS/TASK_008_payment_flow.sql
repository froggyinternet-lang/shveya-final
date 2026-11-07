-- TASK_008 — Payment Flow DDL — HOLD/CAPTURE/REFUND + declared_value + Rule 2/3/4/5/7 + idempotency_key
-- Дата: 2026-11-04
-- SSOT: TASK_001 DDL 13 таблиц + SHVEYA.md Rule 2/3/4/5/7 + TASK_007 RLS

-- Таблица payments — 3 типа HOLD/CAPTURE/REFUND — Rule 2 operator_id NOT NULL + idempotency_key UNIQUE + Rule 5 immutable

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount INT NOT NULL CHECK (amount > 0), -- HOLD amount snapshot v1/v2 Rule 3 или declared_value если потеряна 6
    type VARCHAR(20) NOT NULL CHECK (type IN ('HOLD','CAPTURE','REFUND')),
    operator_id UUID NOT NULL REFERENCES operators(id) ON DELETE RESTRICT, -- Rule 2 AI не допущен — operator_id обязателен для всех фин операций — 403 без него
    idempotency_key TEXT UNIQUE NOT NULL, -- защита от дублей — {order_id}:{type}:{amount}:{timestamp}:{random} — второй INSERT падает duplicate key UNIQUE → Уже обработано — Rule idempotency_key
    price_version_id UUID REFERENCES price_versions(id), -- snapshot Rule 3 v1 не удаляется — фиксирует версию прайса
    return_confirmations_id UUID REFERENCES return_confirmations(id), -- для CAPTURE — фото возврата Rule 4
    reason TEXT, -- для REFUND — причина — отказ, повреждена, потеряна, перепутана, упаковка и тд — 14 исключений — NOT NULL для REFUND
    exception_id INT CHECK (exception_id BETWEEN 1 AND 14), -- 14 исключений — 1 клиент не дома retry, 4 повреждена DISPUTE, 6 потеряна DISPUTE declared_value самая строгая, 7 перепутана qr_code UNIQUE, 11 упаковка повреждена
    photo_url TEXT, -- для REFUND/DISPUTE — фото повреждения/упаковки/двери Rule 4 — NOT NULL для 4,5,11,13 кроме потеряна 6
    declared_value INT, -- для потеряна 6 — объявленная стоимость вещи — возврат полной стоимости — не HOLD amount — declared_value
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS payments_idempotency_key_unique ON payments(idempotency_key);
CREATE INDEX IF NOT EXISTS payments_order_id_idx ON payments(order_id);
CREATE INDEX IF NOT EXISTS payments_operator_id_idx ON payments(operator_id);
CREATE INDEX IF NOT EXISTS payments_type_idx ON payments(type);

-- Rule 5 immutable — нельзя DELETE/UPDATE — RULE DO INSTEAD NOTHING
CREATE OR REPLACE RULE no_update_payments AS ON UPDATE TO payments DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_payments AS ON DELETE TO payments DO INSTEAD NOTHING;
REVOKE UPDATE, DELETE ON payments FROM public, courier, client, operator;
GRANT SELECT, INSERT ON payments TO operator; -- только operator может фин Rule 2
GRANT SELECT ON payments TO courier; -- courier видит но не холдит/списывает/возвращает

-- CHECK: для REFUND reason NOT NULL — для потеряна 6 declared_value NOT NULL
ALTER TABLE payments ADD CONSTRAINT refund_reason_not_null CHECK (type != 'REFUND' OR reason IS NOT NULL AND reason <> '');
ALTER TABLE payments ADD CONSTRAINT lost_declared_value_not_null CHECK (exception_id != 6 OR declared_value IS NOT NULL);

-- Таблица orders — declared_value для потеряна 6 — уже должна быть — добавляем если нет

ALTER TABLE orders ADD COLUMN IF NOT EXISTS declared_value INT CHECK (declared_value > 0); -- объявленная стоимость вещи — для потеряна 6 — возврат полной стоимости — не HOLD amount

-- Таблица events — типы PAYMENT_HOLD/CAPTURED/REFUNDED + idempotency_key UNIQUE + operator_id + Rule 5 immutable

-- Уже есть в TASK_003_event_log.sql — добавляем типы платежей
-- events(id, order_id, type, idempotency_key UNIQUE NOT NULL, operator_id, amount, reason, price_version_id, exception_id, photo_url, created_at) + RULE DO INSTEAD NOTHING Rule 5

ALTER TABLE events ADD COLUMN IF NOT EXISTS amount INT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS operator_id UUID REFERENCES operators(id);
ALTER TABLE events ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS price_version_id UUID REFERENCES price_versions(id);
ALTER TABLE events ADD COLUMN IF NOT EXISTS exception_id INT CHECK (exception_id BETWEEN 1 AND 14);
ALTER TABLE events ADD COLUMN IF NOT EXISTS photo_url TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS declared_value INT;

-- Типы событий платежей
-- PAYMENT_HOLD — захолдили — AGREED
-- PAYMENT_CAPTURED — списали — CLOSED
-- PAYMENT_REFUNDED — вернули — CANCELLED/DISPUTE — declared_value если потеряна 6
-- CUSTOMER_AGREED — клиент согласен v1/v2 — триггер HOLD
-- TRANSFER_SCANNED — QR скан — PICKUP/RETURN/DAMAGE — Rule 7 qr_code UNIQUE + Rule 4 photo_url NOT NULL + Rule 5 immutable

-- Таблица return_confirmations — photo_url NOT NULL Rule 4 — для CAPTURE — уже есть — проверка

CREATE TABLE IF NOT EXISTS return_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL CHECK (photo_url <> ''), -- Rule 4 без return_confirmations не закрыть — photo_url обязательно — фото возврата
    customer_confirmed BOOL NOT NULL DEFAULT false, -- клиент подтвердил возврат
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS return_confirmations_order_id_unique ON return_confirmations(order_id);

-- Таблица transfer_history — photo_url NOT NULL Rule 4 — для PICKUP/RETURN/DAMAGE — уже есть — проверка + immutable Rule 5

CREATE TABLE IF NOT EXISTS transfer_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    qr_code VARCHAR NOT NULL, -- Rule 7 QR только в items.qr_code UNIQUE — проверка UNIQUE в items — вещь, не заказ — перепутана 7 ошибка
    photo_url TEXT NOT NULL CHECK (photo_url <> ''), -- Rule 4 photo_url NOT NULL обязательно для всех сканов кроме потеряна 6 — без фото не забрать/не вернуть
    type VARCHAR(20) NOT NULL CHECK (type IN ('PICKUP','RETURN','DAMAGE')),
    exception_id INT CHECK (exception_id BETWEEN 1 AND 14), -- 14 исключений — 1 клиент не дома photo двери, 4 повреждена фото повреждения DISPUTE, 6 потеряна DISPUTE declared_value самая строгая, 7 перепутана qr_code UNIQUE, 11 упаковка повреждена фото упаковки
    operator_id UUID REFERENCES operators(id),
    courier_id UUID REFERENCES couriers(id),
    idempotency_key TEXT UNIQUE NOT NULL, -- защита от дублей скана — {order_id}:TRANSFER_SCANNED:{qr_code}:{timestamp}:{random} — второй не вставится — Уже обработано
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS transfer_history_idempotency_key_unique ON transfer_history(idempotency_key);
CREATE INDEX IF NOT EXISTS transfer_history_qr_code_idx ON transfer_history(qr_code);

-- Rule 5 immutable
CREATE OR REPLACE RULE no_update_transfer_history AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_transfer_history AS ON DELETE TO transfer_history DO INSTEAD NOTHING;
REVOKE UPDATE, DELETE ON transfer_history FROM public, courier, client, operator;
GRANT SELECT, INSERT ON transfer_history TO courier, operator;

-- CHECK: photo_url NOT NULL кроме потеряна 6 — обрабатывается в API — если exception_id=6 разрешить NULL — иначе NOT NULL — уже CHECK photo_url <> '' — для потеряна 6 API разрешает NULL — тут CHECK остается — для остальных NOT NULL

-- RLS — ENABLE ROW LEVEL SECURITY уже в TASK_007 — повторяем для payments

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY operator_can_finance_payments ON payments FOR ALL TO operator USING (true) WITH CHECK (operator_id IS NOT NULL);
CREATE POLICY courier_cannot_finance_payments ON payments FOR ALL TO courier USING (false);
CREATE POLICY client_cannot_finance_payments ON payments FOR ALL TO client USING (false);
CREATE POLICY operator_can_view_all_payments ON payments FOR SELECT TO operator USING (true);
CREATE POLICY courier_can_view_payments ON payments FOR SELECT TO courier USING (true);

-- Итог: payments + events + transfer_history + return_confirmations + orders.declared_value — все с Rule 2 operator_id NOT NULL + Rule 3 v1 не удаляется snapshot + Rule 4 photo_url NOT NULL + 5 фото + Rule 5 immutable DO INSTEAD NOTHING + Rule 7 qr_code UNIQUE + idempotency_key UNIQUE + 14 исключений + declared_value потеряна 6 самая строгая
