-- TASK_009 — Analytics SQL — 9 запросов — 8 статусов + 14 исключений + operator_id + declared_value + qr_code + photo_url + v1/v2/v3 + idempotency_key
-- Дата: 2026-11-04
-- SSOT: TASK_001 DDL 13 таблиц + SHVEYA.md Rule 2/3/4/5/7 + TASK_008 Payments + TASK_007 Security

-- 1. Сколько по статусам 8 + CANCELLED/DISPUTE — 10 статусов

SELECT status, COUNT(*) as count FROM orders GROUP BY status ORDER BY 
CASE status 
WHEN 'NEW' THEN 1 
WHEN 'ESTIMATED' THEN 2 
WHEN 'AGREED' THEN 3 
WHEN 'IN_WORK' THEN 4 
WHEN 'READY' THEN 5 
WHEN 'OUT_FOR_DELIVERY' THEN 6 
WHEN 'DELIVERED' THEN 7 
WHEN 'CLOSED' THEN 8 
WHEN 'CANCELLED' THEN 9 
WHEN 'DISPUTE' THEN 10 
ELSE 11 END;
-- NEW→ESTIMATED→AGREED→IN_WORK→READY→OUT_FOR_DELIVERY→DELIVERED→CLOSED — 8 шагов State Machine + CANCELLED 5,13 + DISPUTE 4,6,11,12 — 14 исключений

-- 2. По курьерам — сколько забрал/вернул/исключений 14 + трекинг

SELECT c.name as courier, COUNT(th.id) as scans, COUNT(CASE WHEN th.type='PICKUP' THEN 1 END) as pickups, COUNT(CASE WHEN th.type='RETURN' THEN 1 END) as returns, COUNT(CASE WHEN th.exception_id IS NOT NULL THEN 1 END) as exceptions_14 FROM couriers c LEFT JOIN transfer_history th ON th.courier_id=c.id GROUP BY c.name ORDER BY scans DESC;
-- Курьер + трекинг + 14 исключений — 1 не дома retry + фото двери Rule 4, 4 повреждена DISPUTE фото повреждения, 6 потеряна declared_value DISPUTE самая строгая operator_id Rule 2, 7 перепутана qr_code UNIQUE Rule 7, 11 упаковка повреждена фото упаковки DISPUTE

-- 3. По операторам operator_id Rule 2 — сколько HOLD/CAPTURE/REFUND — Rule 2 AI не допущен — только оператор может фин — 403 без operator_id

SELECT o.name as operator, COUNT(p.id) as payments, COUNT(CASE WHEN p.type='HOLD' THEN 1 END) as holds, COUNT(CASE WHEN p.type='CAPTURE' THEN 1 END) as captures, COUNT(CASE WHEN p.type='REFUND' THEN 1 END) as refunds, SUM(CASE WHEN p.type='CAPTURE' THEN p.amount ELSE 0 END) as captured_amount, SUM(CASE WHEN p.type='REFUND' THEN p.amount ELSE 0 END) as refunded_amount, SUM(CASE WHEN p.exception_id=6 THEN p.declared_value ELSE 0 END) as declared_value_refunded_lost_6 FROM operators o LEFT JOIN payments p ON p.operator_id=o.id GROUP BY o.name ORDER BY payments DESC;
-- operator_id NOT NULL Rule 2 — все фин операции только оператор — HOLD/CAPTURE/REFUND — без operator_id 403 — AI не допущен — dropdown Выберите оператора Rule 2

-- 4. По исключениям 14 — сколько каждого + фото + DISPUTE/CANCELLED + declared_value потеряна 6

SELECT exception_id, 
CASE exception_id 
WHEN 1 THEN '1 клиент не дома retry' 
WHEN 2 THEN '2 адрес неверный' 
WHEN 3 THEN '3 клиент перенес' 
WHEN 4 THEN '4 повреждена при заборе DISPUTE' 
WHEN 5 THEN '5 отказался при доставке CANCELLED' 
WHEN 6 THEN '6 потеряна DISPUTE declared_value самая строгая' 
WHEN 7 THEN '7 перепутана qr_code UNIQUE' 
WHEN 8 THEN '8 курьер опоздал' 
WHEN 9 THEN '9 дверь не открыли' 
WHEN 10 THEN '10 клиент не отвечает' 
WHEN 11 THEN '11 упаковка повреждена DISPUTE' 
WHEN 12 THEN '12 вещь грязная после ремонта DISPUTE' 
WHEN 13 THEN '13 клиент передумал CANCELLED' 
WHEN 14 THEN '14 форс-мажор' 
END as exception_name, COUNT(*) as count, COUNT(CASE WHEN photo_url IS NOT NULL THEN 1 END) as with_photo_Rule4, COUNT(CASE WHEN exception_id IN (4,6,11,12) THEN 1 END) as dispute_count, COUNT(CASE WHEN exception_id IN (5,13) THEN 1 END) as cancelled_count FROM transfer_history WHERE exception_id IS NOT NULL GROUP BY exception_id ORDER BY exception_id;
-- 14 исключений — все требуют photo_url NOT NULL Rule 4 кроме потеряна 6 — 4,6,11,12 → DISPUTE + investigation + REFUND operator_id Rule 2 — 5,13 → CANCELLED + REFUND operator_id — 6 потеряна → declared_value самая строгая — DISPUTE + investigation + REFUND declared_value + operator_id Rule 2 — без фото — единственное без photo_url

-- 5. По declared_value — сколько потеряна 6 + сумма declared_value REFUND — самая строгая

SELECT COUNT(*) as lost_6_count, SUM(declared_value) as total_declared_value_refunded, AVG(declared_value) as avg_declared_value, MIN(declared_value) as min_declared, MAX(declared_value) as max_declared FROM payments WHERE exception_id=6;
-- потеряна 6 — DISPUTE + investigation + REFUND declared_value — возврат полной объявленной стоимости — не HOLD amount — пример HOLD 1000 ремонт, declared_value 5000 платье — при потере возврат 5000 — защита клиента — требует operator_id NOT NULL Rule 2 — 403 без operator_id — самая строгая

-- 6. По qr_code UNIQUE Rule 7 — сколько сканов + ошибки перепутана 7 — вещь, не заказ

SELECT qr_code, COUNT(*) as scans, COUNT(DISTINCT order_id) as orders, COUNT(CASE WHEN exception_id=7 THEN 1 END) as confused_7_errors FROM transfer_history GROUP BY qr_code ORDER BY scans DESC;
-- items.qr_code UNIQUE NOT NULL — только в items — не в orders — вещь, не заказ — QR проверяется в items — перепутана 7 ошибка QR не совпадает — нельзя выдать не ту вещь — transfer_history qr_code + items.qr_code UNIQUE Rule 7 — скан проверяет UNIQUE — не совпадает → ошибка перепутана 7

-- 7. По photo_url Rule 4 — сколько без фото — Нет фото Rule 4 — 5 фото этапов — Quality Gate

SELECT COUNT(*) as total_transfers, COUNT(CASE WHEN photo_url IS NOT NULL AND photo_url <> '' THEN 1 END) as with_photo_Rule4, COUNT(*) - COUNT(CASE WHEN photo_url IS NOT NULL AND photo_url <> '' THEN 1 END) as without_photo_Rule4, COUNT(CASE WHEN exception_id=6 THEN 1 END) as lost_6_no_photo_allowed FROM transfer_history;
-- transfer_history.photo_url TEXT NOT NULL Rule 4 — без фото не забрать/не вернуть — PICKUP/RETURN/DAMAGE все требуют фото кроме потеряна 6 — без фото кнопка disabled + Нет фото забора/возврата Rule 4 — 5 фото этапов — Прием + Дефектовка + До + После + Возврат — Quality Gate 6 чеков — 5 фото? — без фото не CLOSED

-- 8. По v1/v2/v3 Rule 3 — сколько v1, v2, v3 — история версий — v1 не удаляется — Price Lock snapshot

SELECT version, COUNT(*) as count, COUNT(DISTINCT price_version_id) as distinct_snapshots FROM estimates GROUP BY version ORDER BY version;
-- price_versions immutable — v1 не удаляется — новая версия v2 создается рядом — старая остается аудит — estimates version INT + price_version_id snapshot — даже если прайс поменяется, у заказа старый snapshot — история v1 1000 → v2 1200 — v1 остается — Rule 3 нельзя менять цену без версии — snapshot price_version_id — HOLD по snapshot Rule 3 — дашборд показывает историю v1,v2,v3

-- 9. По idempotency_key — сколько дублей отклонено — Уже обработано — защита от дублей — 10 атак

SELECT type, COUNT(*) as total_events, COUNT(DISTINCT idempotency_key) as unique_keys, COUNT(*) - COUNT(DISTINCT idempotency_key) as duplicates_blocked FROM events GROUP BY type ORDER BY total_events DESC;
-- events.idempotency_key TEXT UNIQUE NOT NULL — защита от дублей — Согласен/Скан/Списать/Холд/Рефанд — key = {order_id}:{event_type}:{timestamp}:{random} — второй INSERT падает duplicate key violation UNIQUE → Уже обработано — деньги не списываются/холдятся/возвращаются 2 раза — атаки 1 Дубль Согласен, 2 Дубль QR скан, 3 Дубль Списать — все закрыты idempotency_key UNIQUE — duplicate key → Уже обработано

-- Дополнительные — по HOLD/CAPTURE/REFUND + Quality Gate

SELECT type, COUNT(*) as count, SUM(amount) as total_amount, AVG(amount) as avg_amount FROM payments GROUP BY type;
-- HOLD — AGREED после Согласен v1/v2 — operator_id NOT NULL Rule 2 + snapshot Rule 3 + idempotency_key UNIQUE
-- CAPTURE — CLOSED после возврата — operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + 5 фото + Quality Gate 6 чеков + idempotency_key UNIQUE
-- REFUND — CANCELLED/DISPUTE — operator_id NOT NULL Rule 2 + reason + idempotency_key UNIQUE + для потеряна 6 declared_value самая строгая

-- Quality Gate — сколько CLOSED без 5 фото — не должно быть

SELECT COUNT(*) as closed_without_5_photos FROM orders WHERE status='CLOSED' AND id NOT IN (SELECT order_id FROM return_confirmations WHERE photo_url IS NOT NULL) ;
-- Quality Gate 6 чеков — 5 фото? QR? Цена? operator_id? immutable? idempotency_key? — без 5 фото нельзя CLOSED — без return_confirmations photo_url NOT NULL Rule 4 — Нет фото возврата Rule 4 — без operator_id NOT NULL Rule 2 — Выберите оператора Rule 2
