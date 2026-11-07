# TASK_008 — HOLD/CAPTURE/REFUND — 3 операции + Rule 2/3/4/5/7 + idempotency_key
Дата: 2026-11-04
SSOT: SHVEYA.md v2.3 + TASK_007 Security 10 атак + TASK_006 Quality Gate 5 фото + TASK_003 idempotency_key

## 3 операции платежей

### 1. HOLD — AGREED после Согласен v1/v2 — захолдить деньги

Когда: клиент жмет [✅ Согласен v1] или [✅ Согласен v2] в Telegram + оператор выбран
Триггер: CUSTOMER_AGREED v1/v2 + operator_id NOT NULL Rule 2 + amount snapshot price_version_id Rule 3 + idempotency_key UNIQUE

Что требует:
- operator_id UUID NOT NULL Rule 2 AI не допущен — без него 403 Forbidden + dropdown "Выберите оператора — Rule 2 AI не допущен" + кнопка [Захолдить] disabled
- amount snapshot — цена из estimates + price_versions snapshot — v1 1000 остается даже если прайс поменялся Rule 3 v1 не удаляется
- price_version_id UUID snapshot — фиксирует версию прайса
- idempotency_key TEXT UNIQUE NOT NULL — key = {order_id}:PAYMENT_HOLD:{amount}:{timestamp}:{random} — второй холд падает duplicate key UNIQUE → "Уже обработано"
- estimates version INT — версия оценки v1/v2/v3

Что пишет:
- payments(id, order_id, amount, type=HOLD, operator_id NOT NULL Rule 2, idempotency_key UNIQUE NOT NULL, price_version_id snapshot Rule 3, created_at) — HOLD
- events(id, order_id, type=PAYMENT_HOLD, idempotency_key UNIQUE NOT NULL, operator_id NOT NULL, amount, price_version_id snapshot, created_at) — immutable Rule 5 RULE DO INSTEAD NOTHING
- transfer_history immutable Rule 5 — лог не подделать

API: POST /api/payment/hold {order_id, amount, operator_id NOT NULL, price_version_id snapshot, idempotency_key UNIQUE, version}
- Без operator_id → 403 Forbidden Rule 2 AI не допущен
- Без idempotency_key → 400 idempotency_key NOT NULL
- Второй вызов с тем же idempotency_key → 409 Conflict duplicate key UNIQUE → "Уже обработано" — деньги не холдятся 2 раза
- Без price_version_id → 400 price_version_id snapshot Rule 3

Frontend:
- Operator Dashboard: кнопка [Захолдить платеж] disabled пока нет operator_id NOT NULL Rule 2 + текст "Выберите оператора — Rule 2 AI не допущен"
- Telegram клиенту: "Оплата захолдирована 1000 руб v1 — В работе у мастера"

Защита от дублей: idempotency_key UNIQUE {order_id}:PAYMENT_HOLD:{amount}:{timestamp}:{random} — второй не вставится

### 2. CAPTURE — DELIVERED→CLOSED — списать при возврате

Когда: курьер вернул вещь + фото возврата + customer_confirmed + оператор жмет [Списать]
Триггер: RETURN скан + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + 5 фото этапов + Quality Gate 6 чеков + operator_id NOT NULL Rule 2 + idempotency_key UNIQUE

Что требует:
- operator_id UUID NOT NULL Rule 2 — без него 403 + [Списать] disabled "Выберите оператора — Rule 2"
- return_confirmations photo_url TEXT NOT NULL Rule 4 — фото возврата обязательно — без него "Нет фото возврата — Rule 4" — нельзя закрыть CLOSED
- customer_confirmed BOOL — клиент подтвердил возврат
- 5 фото этапов: Прием + Дефектовка + До ремонта + После ремонта + Возврат — все photo_url NOT NULL Rule 4
- Quality Gate 6 чеков: 5 фото? QR совпадает items.qr_code UNIQUE Rule 7? Цена зафиксирована price_version_id snapshot Rule 3? operator_id есть Rule 2? immutable Rule 5? idempotency_key?
- idempotency_key UNIQUE NOT NULL — {order_id}:PAYMENT_CAPTURED:{amount}:{timestamp}:{random} — второй списать падает duplicate key → Уже обработано
- amount — из HOLD — та же сумма что холдили snapshot Rule 3

Что пишет:
- payments CAPTURE — type=CAPTURE, amount=HOLD amount, operator_id NOT NULL Rule 2, idempotency_key UNIQUE, return_confirmations_id
- events PAYMENT_CAPTURED — idempotency_key UNIQUE, operator_id NOT NULL, amount, return_confirmations photo_url NOT NULL
- orders status CLOSED — закрыт + чек списан + 5 фото сохранены

API: POST /api/payment/capture {order_id, operator_id NOT NULL, return_confirmations_id, photo_url NOT NULL, idempotency_key UNIQUE, amount}
- Без operator_id → 403 Rule 2
- Без photo_url → 400 "Нет фото возврата — Rule 4"
- Без 5 фото → 400 "Нет 5 фото этапов — Quality Gate"
- Без return_confirmations → 400 return_confirmations NOT NULL Rule 4
- Второй вызов с тем же idempotency_key → 409 "Уже обработано" — деньги не списываются 2 раза

Frontend:
- Operator: [Списать] disabled пока нет return_confirmations photo_url NOT NULL Rule 4 + 5 фото + operator_id NOT NULL Rule 2
- Telegram клиенту: "Заказ закрыт Чек 1000 руб списан Спасибо! Фото 5 этапов сохранены"

Защита: idempotency_key UNIQUE + photo_url NOT NULL Rule 4 + operator_id NOT NULL Rule 2 + 5 фото Quality Gate

### 3. REFUND — CANCELLED/DISPUTE — вернуть

Когда: клиент отказался при оценке или доставке CANCELLED 5,13 + повреждена при заборе 4 + потеряна 6 + перепутана 7 + упаковка повреждена 11 — DISPUTE/CANCELLED — оператор жмет [Возврат денег]
Триггер: CANCELLED/DISPUTE + reason TEXT NOT NULL + operator_id NOT NULL Rule 2 + idempotency_key UNIQUE + для потеряна 6 amount=declared_value + фото если есть Rule 4

Что требует:
- operator_id UUID NOT NULL Rule 2 — без него 403 — только оператор может вернуть Rule 2 AI не допущен
- reason TEXT NOT NULL — причина возврата — отказ, повреждена, потеряна, перепутана, упаковка и тд — 14 исключений
- idempotency_key UNIQUE NOT NULL — {order_id}:PAYMENT_REFUNDED:{amount}:{timestamp}:{random} — второй возврат падает duplicate key → Уже обработано
- Для потеряна 6: amount=declared_value — возврат полной объявленной стоимости — самая строгая — DISPUTE + investigation
- Для повреждена 4: photo_url NOT NULL повреждения Rule 4 обязательно — DISPUTE + investigation + REFUND operator_id
- Для упаковка 11: photo_url NOT NULL упаковки Rule 4 — DISPUTE + investigation + REFUND
- Для остальных CANCELLED 5,13: photo_url NOT NULL вещи Rule 4 — CANCELLED + REFUND operator_id

Что пишет:
- payments REFUND — type=REFUND, amount=HOLD amount или declared_value если потеряна 6, operator_id NOT NULL Rule 2, reason, idempotency_key UNIQUE, photo_url если есть
- events PAYMENT_REFUNDED — idempotency_key UNIQUE, operator_id NOT NULL, amount, reason, photo_url если есть, exception_id
- orders status CANCELLED/DISPUTE — причина + investigation если DISPUTE

API: POST /api/payment/refund {order_id, amount (declared_value если потеряна 6 иначе HOLD amount), operator_id NOT NULL, reason TEXT NOT NULL, idempotency_key UNIQUE, photo_url TEXT если есть Rule 4, exception_id}
- Без operator_id → 403 Rule 2 AI не допущен
- Без reason → 400 reason NOT NULL
- Без idempotency_key → 400 idempotency_key NOT NULL
- Второй вызов с тем же idempotency_key → 409 "Уже обработано" — деньги не возвращаются 2 раза
- Для потеряна 6 без declared_value → 400 declared_value required — самая строгая
- Для повреждена 4 без photo_url → 400 "Нет фото повреждения — Rule 4"

Frontend:
- Operator: [Возврат денег] disabled пока нет operator_id NOT NULL Rule 2 + reason + для потеряна 6 declared_value
- Telegram клиенту: "Отменен причина + возврат денег PAYMENT_REFUNDED" или "Спор investigation + возврат declared_value если потеряна 6"

Защита: idempotency_key UNIQUE + operator_id NOT NULL Rule 2 + reason NOT NULL + photo_url NOT NULL Rule 4 для повреждений + declared_value для потеряна 6

## Итого 3 операции = 10 атак закрыты

- idempotency_key UNIQUE — защита от дублей Холд/Списать/Возврат/Согласен — duplicate key → Уже обработано — атаки 1,2,3
- Rule 2 operator_id NOT NULL — все фин операции только оператор — 403 без operator_id — AI не допущен — атаки 3,4,9
- Rule 4 photo_url NOT NULL + 5 фото + Quality Gate 6 чеков — без фото не закрыть CLOSED + не выдать курьеру — атаки 8,9
- Rule 5 immutable RULE DO INSTEAD NOTHING — events + transfer_history + payments нельзя DELETE/UPDATE — только просмотр — атаки 5,10
- Rule 3 v1 не удаляется + snapshot price_version_id — цена зафиксирована — даже если прайс поменялся, холд по старому snapshot — атака 6
- Rule 7 qr_code UNIQUE — вещь, не заказ — перепутана 7 ошибка — атаки 7,10
- 14 исключений — потеряна 6 самая строгая DISPUTE + investigation + REFUND declared_value + operator_id Rule 2 — атаки 9,10
