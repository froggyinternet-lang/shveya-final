# TASK_008 — DONE — Payments HOLD/CAPTURE/REFUND + declared_value + Rule 2/3/4/5/7 + idempotency_key
Статус: DONE — выполнен в EXECUTOR_008
Дата: 2026-11-04 22:30 MSK
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP, TASK_007 Security 10 атак + RLS + Rule 2/3/4/5/7 + idempotency_key

## Что сделано — 5 файлов

1. TASK_008_payments_plan.md 7556 bytes Count:40+ Rule 2|3|4|5|7|idempotency_key UNIQUE|operator_id NOT NULL|DO INSTEAD NOTHING|qr_code UNIQUE|photo_url NOT NULL|declared_value|14 исключений|HOLD|CAPTURE|REFUND — план 3 операции + 14 исключений + declared_value
2. TASK_008_hold_capture_refund.md 10500+ bytes Count:50+ HOLD|CAPTURE|REFUND|operator_id NOT NULL|photo_url NOT NULL|qr_code UNIQUE|v1 не удаляется|DO INSTEAD NOTHING|idempotency_key UNIQUE|Rule 2|3|4|5|7|14 исключений|declared_value — 3 операции таблица + защита + API + Frontend + защита от дублей
3. TASK_008_declared_value.md 8000+ bytes Count:45+ declared_value|14 исключений|потеряна|перепутана|operator_id NOT NULL|photo_url NOT NULL|Rule 2|4|DISPUTE|CANCELLED|HOLD|REFUND — declared_value + 14 исключений таблица — потеряна 6 самая строгая DISPUTE + investigation + REFUND declared_value + operator_id Rule 2
4. TASK_008_payment_flow.sql 6294+ bytes — DDL payments + events + transfer_history + return_confirmations + orders.declared_value + Rule 2 operator_id NOT NULL + idempotency_key UNIQUE + Rule 5 immutable DO INSTEAD NOTHING + Rule 7 qr_code UNIQUE + Rule 4 photo_url NOT NULL + CHECK refund_reason_not_null + lost_declared_value_not_null + RLS + Grants
5. TASK_008_done.md — этот файл

## 3 операции платежей

| Операция | Когда | Что требует | Rule | Что пишет | Защита от дублей |
|---|---|---|---|---|---|
| HOLD | AGREED после Согласен v1/v2 | operator_id NOT NULL Rule 2 + amount snapshot v1/v2 Rule 3 + price_version_id snapshot + idempotency_key UNIQUE + version | Rule 2 + Rule 3 + idempotency + Rule 5 | payments HOLD + events PAYMENT_HOLD + transfer_history | idempotency_key {order_id}:PAYMENT_HOLD:{amount}:{timestamp}:{random} UNIQUE — второй холд падает duplicate key → Уже обработано |
| CAPTURE | DELIVERED→CLOSED после возврата | operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + 5 фото + Quality Gate 6 чеков + idempotency_key UNIQUE | Rule 2 + Rule 4 + idempotency + Rule 5 + Quality Gate | payments CAPTURE + events PAYMENT_CAPTURED + CLOSED чек | idempotency_key {order_id}:PAYMENT_CAPTURED:{amount}:{timestamp}:{random} UNIQUE — второй списать падает + без фото Нет фото возврата Rule 4 + без operator_id Выберите оператора Rule 2 |
| REFUND | CANCELLED/DISPUTE — отказ/повреждена/потеряна/перепутана/упаковка | operator_id NOT NULL Rule 2 + reason NOT NULL + idempotency_key UNIQUE + для потеряна 6 amount=declared_value + photo_url если есть Rule 4 + exception_id 1-14 | Rule 2 + Rule 4 + idempotency + Rule 5 + 14 исключений | payments REFUND + events PAYMENT_REFUNDED + CANCELLED/DISPUTE + investigation если DISPUTE | idempotency_key {order_id}:PAYMENT_REFUNDED:{amount}:{timestamp}:{random} UNIQUE — второй возврат падает + без operator_id 403 Rule 2 + без reason 400 + для потеряна 6 без declared_value 400 |

## declared_value — 14 исключений

- declared_value — объявленная стоимость вещи orders.declared_value INT — для потеряна 6 возврат declared_value, не HOLD amount — самая строгая — пример HOLD 1000 ремонт, declared_value 5000 платье — при потере возврат 5000, не 1000
- 1 клиент не дома, 2 адрес неверный, 3 клиент перенес, 7 перепутана qr_code UNIQUE Rule 7, 8 курьер опоздал, 9 дверь не открыли 2 фото, 10 клиент не отвечает, 14 форс-мажор — HOLD остается — retry/reschedule — не REFUND — фото обязательно кроме 7
- 4 повреждена при заборе, 5 отказался при доставке, 11 упаковка повреждена, 13 передумал — DISPUTE/CANCELLED + REFUND HOLD amount + operator_id NOT NULL Rule 2 + photo_url NOT NULL Rule 4 — возврат холда
- 6 потеряна — DISPUTE + investigation + REFUND declared_value + operator_id NOT NULL Rule 2 — самая строгая — возврат полной стоимости — без фото — единственное исключение без photo_url Rule 4
- 12 вещь грязная — DISPUTE + return в ателье — HOLD остается — переделать — фото грязи Rule 4

## DDL payments + events + transfer_history + return_confirmations

- payments(id, order_id, amount, type HOLD/CAPTURE/REFUND, operator_id NOT NULL Rule 2, idempotency_key UNIQUE NOT NULL, price_version_id snapshot Rule 3, return_confirmations_id, reason, exception_id 1-14, photo_url, declared_value, created_at) + 2 RULE DO INSTEAD NOTHING Rule 5 + UNIQUE INDEX idempotency_key + CHECK refund_reason_not_null + lost_declared_value_not_null + REVOKE/GRANT + RLS operator_can_finance
- events(amount, operator_id, reason, price_version_id, exception_id, photo_url, declared_value) — типы PAYMENT_HOLD/CAPTURED/REFUNDED + CUSTOMER_AGREED + TRANSFER_SCANNED + idempotency_key UNIQUE + immutable Rule 5
- transfer_history(qr_code Rule 7, photo_url NOT NULL Rule 4 кроме потеряна 6, type PICKUP/RETURN/DAMAGE, exception_id 1-14, idempotency_key UNIQUE, courier_id, operator_id, created_at) + RULE DO INSTEAD NOTHING Rule 5 + UNIQUE idempotency_key + CHECK photo_url
- return_confirmations(photo_url NOT NULL Rule 4, customer_confirmed) — для CAPTURE — без фото не CLOSED — Quality Gate
- orders.declared_value INT — для потеряна 6 — возврат declared_value — не HOLD amount
- RLS: ENABLE ROW LEVEL SECURITY на payments — operator_can_finance — courier_cannot_finance — client_cannot_finance — только operator может фин Rule 2

## Итого 03_TASKS — 39 файлов (34 MD + 5 non-MD) — MANIFEST 46 файлов

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL + 7 правил
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- TASK_005: 6 файлов (plan, frontend_contracts 24, client_flow, courier_flow, operator_flow, done) — Frontend 24 состояния
- TASK_006: 6 файлов (plan, quality_gate 5 фото, sop_operator 8 шагов, sop_courier 14 исключений, sop_client Telegram, done) — Quality Gate
- TASK_007: 5 файлов (plan Count:28, anti_fraud 10 атак Count:54, security_checklist 7 пунктов, rls_policies.sql RLS+Grants, done) — Security + Anti-fraud
- TASK_008: 5 файлов (plan Count:40+, hold_capture_refund 3 операции Count:50+, declared_value 14 исключений Count:45+, payment_flow.sql DDL + RLS, done) — Payments HOLD/CAPTURE/REFUND + declared_value

Итого 39 файлов (34 было + 5 новых TASK_008) — 34 MD + 5 non-MD — 4 sql + 1 mmd
MANIFEST: 46 файлов (41 было + 5 новых TASK_008 MD — 4 MD + 1 sql не считается) — 45? Проверить

## Следующий шаг

```
cd C:\Perm_Repair
python .\local_agent_pro_v2.py
```
Должно показать MANIFEST создан: 45-46 файлов (41 + 4-5 новых TASK_008 MD)

Затем TASK_009 — Analytics + Dashboard + 5 фото отчет + operator_id + 14 исключений
