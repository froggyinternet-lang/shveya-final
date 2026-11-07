# TASK_008 — Payments — HOLD/CAPTURE/REFUND + declared_value + Rule 2 + 14 исключений — PLAN
Дата: 2026-11-04 22:30 MSK
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_008
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP, TASK_007 Security 10 атак + RLS + Rule 2/3/4/5/7 + idempotency_key

## Цель TASK_008

Вшить платежную систему HOLD→CAPTURE/REFUND с защитой Constitution:

- HOLD: AGREED → захолдить деньги при согласии клиента Согласен v1/v2 — требует operator_id NOT NULL Rule 2 + idempotency_key UNIQUE
- CAPTURE: DELIVERED → CLOSED — списать при возврате — требует operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + 5 фото + idempotency_key UNIQUE
- REFUND: CANCELLED/DISPUTE — вернуть — требует operator_id NOT NULL Rule 2 + reason + idempotency_key UNIQUE + для потеряна 6 → declared_value
- Rule 2: AI не допущен — все фин операции только оператор — 403 без operator_id
- Rule 5: immutable — payments + events + transfer_history нельзя DELETE/UPDATE — RULE DO INSTEAD NOTHING
- idempotency_key UNIQUE — защита от дублей Списать/Холд/Возврат/Согласен — duplicate key → Уже обработано
- 14 исключений: 1 клиент не дома retry, 4 повреждена при заборе DISPUTE + фото, 6 потеряна DISPUTE + declared_value + operator_id самая строгая, 7 перепутана qr_code UNIQUE проверка, 11 упаковка повреждена фото
- Price Lock: v1 не удаляется — snapshot price_version_id — даже если прайс поменялся, холд по старому snapshot

## Что делать в EXECUTOR_008 — 5 файлов

### 1. TASK_008_payments_plan.md — этот файл — план

### 2. TASK_008_hold_capture_refund.md — HOLD/CAPTURE/REFUND — 3 операции + таблица

| Операция | Когда | Триггер | Что требует | Rule | Что пишет | API | Защита от дублей |
|---|---|---|---|---|---|---|---|
| HOLD | AGREED после Согласен v1/v2 | Клиент жмет Согласен v1/v2 + operator_id | operator_id NOT NULL Rule 2 + amount snapshot v1/v2 + price_version_id + idempotency_key UNIQUE + estimates version | Rule 2 + Rule 3 + idempotency + Rule 5 | payments amount HOLD + events PAYMENT_HOLD + transfer_history | POST /api/payment/hold {order_id, amount, operator_id NOT NULL, price_version_id snapshot, idempotency_key UNIQUE} | idempotency_key {order_id}:PAYMENT_HOLD:{amount}:{timestamp}:{random} UNIQUE — второй холд падает duplicate key → Уже обработано |
| CAPTURE | DELIVERED→CLOSED после возврата | Курьер вернул + фото возврата + customer_confirmed + operator жмет Списать | operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + 5 фото + idempotency_key UNIQUE + 6 чеков Quality Gate | Rule 2 + Rule 4 + idempotency + Rule 5 + Quality Gate | payments CAPTURE + events PAYMENT_CAPTURED + CLOSED | POST /api/payment/capture {order_id, operator_id NOT NULL, return_confirmations_id, photo_url NOT NULL, idempotency_key UNIQUE} | idempotency_key {order_id}:PAYMENT_CAPTURED:{amount}:{timestamp}:{random} UNIQUE — второй списать падает duplicate key → Уже обработано + без фото — Нет фото возврата Rule 4 + без operator_id — Выберите оператора Rule 2 |
| REFUND | CANCELLED/DISPUTE — клиент отказался/повреждена/потеряна/перепутана/упаковка | Оператор жмет Возврат денег + reason + для потеряна 6 → declared_value | operator_id NOT NULL Rule 2 + reason TEXT NOT NULL + idempotency_key UNIQUE + для потеряна 6 amount=declared_value + фото повреждения если есть Rule 4 + investigation если DISPUTE | Rule 2 + Rule 4 + idempotency + Rule 5 + 14 исключений | payments REFUND + events PAYMENT_REFUNDED + CANCELLED/DISPUTE | POST /api/payment/refund {order_id, amount (declared_value если потеряна 6), operator_id NOT NULL, reason, idempotency_key UNIQUE, photo_url если есть} | idempotency_key {order_id}:PAYMENT_REFUNDED:{amount}:{timestamp}:{random} UNIQUE — второй возврат падает + без operator_id — 403 Rule 2 + без reason — 400 |

### 3. TASK_008_declared_value.md — declared_value + 14 исключений — самая строгая потеряна 6

| # | Исключение | Что делать с платежом | amount | operator_id | photo_url | Что пишет |
|---|---|---|---|---|---|---|
| 1 | клиент не дома | HOLD остается — retry завтра — не REFUND | HOLD amount | — | photo_url NOT NULL двери | transfer_history + exception 1 + retry |
| 2 | адрес неверный | HOLD остается — уточнить адрес | HOLD amount | — | photo_url NOT NULL | exception 2 |
| 3 | клиент перенес | HOLD остается — reschedule | HOLD amount | — | photo_url NOT NULL | exception 3 |
| 4 | повреждена при заборе | DISPUTE + investigation + REFUND | HOLD amount | operator_id NOT NULL Rule 2 | photo_url NOT NULL повреждения Rule 4 обязательно | DISPUTE + events DAMAGE + PAYMENT_REFUNDED operator_id Rule 2 |
| 5 | клиент отказался при доставке | CANCELLED + REFUND | HOLD amount | operator_id NOT NULL Rule 2 | photo_url NOT NULL | CANCELLED 5 + PAYMENT_REFUNDED operator_id |
| 6 | потеряна | DISPUTE + investigation + REFUND declared_value — самая строгая | declared_value | operator_id NOT NULL Rule 2 | — (ничего нет) | DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id Rule 2 — возврат полной объявленной стоимости |
| 7 | перепутана | HOLD остается — ошибка QR не совпадает Rule 7 — не тот QR | HOLD amount | — | — | ошибка qr_code UNIQUE не совпадает Rule 7 — нельзя выдать |
| 8 | курьер опоздал | HOLD остается | HOLD amount | — | photo_url | exception 8 |
| 9 | дверь не открыли | HOLD остается — 2 фото двери с интервалом | HOLD amount | — | photo_url NOT NULL двери | exception 9 |
| 10 | клиент не отвечает | HOLD остается — retry | HOLD amount | — | photo_url | exception 10 |
| 11 | упаковка повреждена | DISPUTE + investigation + REFUND | HOLD amount | operator_id NOT NULL Rule 2 | photo_url NOT NULL упаковки Rule 4 | DISPUTE + investigation + PAYMENT_REFUNDED operator_id |
| 12 | вещь грязная после ремонта | DISPUTE + return в ателье — HOLD остается | HOLD amount | — | photo_url NOT NULL | DISPUTE + return |
| 13 | клиент передумал | CANCELLED + REFUND | HOLD amount | operator_id NOT NULL Rule 2 | photo_url NOT NULL | CANCELLED 13 + PAYMENT_REFUNDED operator_id |
| 14 | форс-мажор | exception + investigation — HOLD остается | HOLD amount | — | photo_url | exception 14 + investigation |

### 4. TASK_008_payment_flow.sql — DDL payments + events + immutable + idempotency_key

- payments(id, order_id, amount, type HOLD/CAPTURE/REFUND, operator_id UUID NOT NULL Rule 2, idempotency_key UNIQUE NOT NULL, reason, created_at) + RULE DO INSTEAD NOTHING Rule 5
- events(id, order_id, type PAYMENT_HOLD/CAPTURED/REFUNDED, idempotency_key UNIQUE NOT NULL, operator_id, amount, reason, created_at) + RULE DO INSTEAD NOTHING Rule 5
- orders(declared_value) — для потеряна 6 — возврат declared_value
- price_versions + estimates snapshot — HOLD по snapshot v1/v2 Rule 3

### 5. TASK_008_done.md — summary

## Критерий готовности

- HOLD/CAPTURE/REFUND таблица 3 операции + Rule 2 + Rule 4 + Rule 5 + idempotency_key UNIQUE + Price Lock v1 не удаляется + 5 фото
- declared_value таблица 14 исключений — потеряна 6 самая строгая — DISPUTE + investigation + REFUND declared_value + operator_id Rule 2
- SQL DDL payments + events + immutable + idempotency_key + operator_id NOT NULL + declared_value
- Все вшивает Constitution SHVEYA.md v2.3 + TASK_007 Security 10 атак + RLS

## Ограничения

- Один файл за раз через container:///
- Бюджет <6K
- Не выполнять 009 пока 008 не DONE
