# TASK_007 — Anti-fraud — 10 атак + защита Constitution
Дата: 2026-11-04
SSOT: SHVEYA.md v2.3 Rule 2/3/4/5/7 + idempotency_key UNIQUE + 14 исключений + 8 шагов

## 10 атак + защита

### 1. Дубль Согласен — клиент 2 раза жмет Согласен v1

Атака: клиент быстро 2 раза жмет [✅ Согласен v1] → пытается списать деньги 2 раза
Защита: events.idempotency_key UNIQUE NOT NULL — key = {order_id}:CUSTOMER_AGREED:{version}:timestamp:random — второй INSERT падает duplicate key violation UNIQUE — показывает "Уже обработано" — деньги не списываются 2 раза
Rule: idempotency_key UNIQUE + Rule 5 immutable + Rule 3 v1 не удаляется
API: POST /api/telegram/callback agree {order_id, version, idempotency_key UNIQUE}
БД: events(idempotency_key UNIQUE NOT NULL) + RULE DO INSTEAD NOTHING

### 2. Дубль QR скан — курьер 2 раза сканирует QR-001

Атака: курьер 2 раза сканирует QR чтобы продублировать забор/возврат
Защита: idempotency_key UNIQUE {order_id}:TRANSFER_SCANNED:{qr_code}:timestamp:random + qr_code UNIQUE в items Rule 7 — второй не вставится — "Уже обработано"
Rule: idempotency_key UNIQUE + Rule 7 QR только в items + Rule 5 immutable transfer_history + Rule 4 photo_url NOT NULL
API: POST /api/transfer/scan PICKUP {qr_code UNIQUE, photo_url NOT NULL, operator_id, idempotency_key UNIQUE}
БД: items.qr_code UNIQUE NOT NULL + transfer_history immutable RULE DO INSTEAD NOTHING + idempotency_key UNIQUE

### 3. Дубль Списать — оператор 2 раза жмет Списать

Атака: оператор 2 раза жмет [Списать] чтобы списать 2 раза
Защита: idempotency_key UNIQUE {order_id}:PAYMENT_CAPTURED:{amount}:{timestamp} + payments.operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + 5 фото — второй падает duplicate key
Rule: idempotency_key UNIQUE + Rule 2 operator_id NOT NULL + Rule 4 photo_url + Rule 5 immutable
API: POST /api/payment/capture {order_id, operator_id NOT NULL, return_confirmations_id, idempotency_key UNIQUE, amount}
БД: payments.operator_id UUID NOT NULL + return_confirmations photo_url NOT NULL + events idempotency_key UNIQUE

### 4. Подделка operator_id — AI пытается списать без оператора Rule 2

Атака: AI/бот пытается вызвать HOLD/CAPTURE/REFUND без оператора — пытается списать деньги без человека
Защита: payments.operator_id UUID NOT NULL + 403 Forbidden без operator_id + UI dropdown "Выберите оператора — Rule 2 AI не допущен" + кнопка disabled пока нет operator_id + backend проверка operator_id NOT NULL Rule 2
Rule: Rule 2 AI не допущен — operator_id обязателен для всех фин операций
API: POST /api/payment/hold {order_id, amount, operator_id NOT NULL, idempotency_key} → 403 если нет operator_id + POST /api/payment/capture + POST /api/payment/refund
БД: payments(operator_id UUID NOT NULL REFERENCES operators) — NOT NULL
Frontend: кнопка [Захолдить][Списать][Возврат] disabled пока нет operator_id — текст "Выберите оператора — Rule 2 AI не допущен"

### 5. Подделка истории — пытается DELETE/UPDATE events + transfer_history Rule 5

Атака: пытается удалить или изменить лог чтобы скрыть мошенничество
Защита: 2 RULE DO INSTEAD NOTHING — CREATE RULE no_update AS ON UPDATE TO events DO INSTEAD NOTHING + CREATE RULE no_delete AS ON DELETE TO events DO INSTEAD NOTHING + то же для transfer_history — нельзя DELETE/UPDATE — только INSERT + SELECT — только просмотр в Dashboard — immutable Rule 5
Rule: Rule 5 нельзя DELETE/UPDATE — immutable
БД: RULE DO INSTEAD NOTHING на events + transfer_history — REVOKE UPDATE, DELETE
Frontend: Operator Dashboard — events + transfer_history только просмотр — нет кнопок удалить/изменить

### 6. Смена цены без версии — меняет цену v1 напрямую Rule 3

Атака: меняет цену 1000 → 1200 без создания v2 — пытается скрыть старую цену
Защита: price_versions immutable — v1 не удаляется — новая версия v2 создается рядом — старая остается аудит — estimates version INT + price_version_id snapshot — даже если прайс поменяется, у заказа старый snapshot — история v1 1000 → v2 1200
Rule: Rule 3 нельзя менять цену без версии — v1 не удаляется
БД: price_versions(id, version, price, created_at) immutable — estimates(price_version_id UUID REFERENCES price_versions, version INT) — version 1,2,3 — v1 не удаляется
API: POST /api/order/estimate {order_id, price_version_id snapshot, version} — создает новую версию, старая не удаляется
Frontend: карточка показывает историю v1,v2,v3 + snapshot price_version_id

### 7. QR в orders — пытается положить QR в orders вместо items Rule 7

Атака: кладет QR в orders чтобы перепутать вещи — отдает не ту вещь
Защита: items.qr_code UNIQUE NOT NULL — только тут — orders без qr_code — вещь, не заказ — QR проверяется в items — перепутана исключение 7 ошибка "QR не совпадает" — нельзя выдать не ту вещь
Rule: Rule 7 QR только в items — qr_code UNIQUE NOT NULL — не в orders
БД: items(qr_code VARCHAR UNIQUE NOT NULL) — orders без qr_code
API: POST /api/order/create {items: [{qr_code UNIQUE, ...}]} — qr_code создается в items, не в orders — POST /api/transfer/scan проверяет items.qr_code UNIQUE
Frontend: Courier скан проверяет UNIQUE в items Rule 7 — если не совпадает — ошибка перепутана 7

### 8. Закрытие без фото — пытается закрыть без photo_url Rule 4

Атака: пытается закрыть CLOSED без фото возврата — скрыть повреждение
Защита: return_confirmations photo_url TEXT NOT NULL + transfer_history photo_url TEXT NOT NULL + 5 фото этапов обязательно — без фото кнопка [Списать] disabled — текст "Нет фото возврата — Rule 4" — нельзя закрыть без фото — Quality Gate 5 фото + 6 чеков
Rule: Rule 4 без return_confirmations не закрыть — photo_url NOT NULL + 5 фото этапов
БД: return_confirmations(photo_url TEXT NOT NULL, customer_confirmed BOOL) + transfer_history(photo_url TEXT NOT NULL)
API: POST /api/transfer/scan PICKUP/RETURN/DAMAGE {photo_url NOT NULL} + POST /api/payment/capture требует return_confirmations photo_url NOT NULL
Frontend: Courier [Подтвердить] disabled пока нет photo_url NOT NULL — Operator [Списать] disabled пока нет return_confirmations + 5 фото

### 9. Потеряна без возврата — теряет вещь и не возвращает declared_value исключение 6

Атака: курьер теряет вещь и не хочет возвращать declared_value — самая строгая
Защита: исключение 6 потеряна → DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id NOT NULL Rule 2 — возврат полной объявленной стоимости — без operator_id нельзя — 403 — investigation + фото если есть — Quality Gate
Rule: Rule 2 operator_id NOT NULL + Rule 4 photo_url если есть + исключение 6 потеряна DISPUTE + declared_value
БД: payments(operator_id NOT NULL) + orders(declared_value) — refund = declared_value
API: POST /api/payment/refund {order_id, amount=declared_value, operator_id NOT NULL, reason=потеряна, idempotency_key UNIQUE} — только оператор Rule 2
Frontend: [Возврат денег] требует operator_id NOT NULL — для потеряна — возврат declared_value

### 10. Перепутана без проверки — отдает не ту вещь исключение 7

Атака: отдает клиенту не ту вещь — перепутал QR
Защита: qr_code UNIQUE проверка в items Rule 7 — скан проверяет UNIQUE — не совпадает → ошибка "QR не совпадает — перепутана 7" — нельзя выдать — transfer_history immutable Rule 5 — лог не подделать — idempotency_key UNIQUE — второй скан не вставится
Rule: Rule 7 QR только в items + Rule 5 immutable + idempotency_key UNIQUE + Rule 4 photo_url
БД: items.qr_code UNIQUE NOT NULL — transfer_history immutable RULE DO INSTEAD NOTHING
API: POST /api/transfer/scan проверяет items.qr_code UNIQUE — если не совпадает → 400 QR не совпадает перепутана 7
Frontend: Courier скан — если QR не совпадает — ошибка + нельзя подтвердить

## Итого 10 атак закрыты Constitution

- idempotency_key UNIQUE — 3 атаки дублей (1,2,3)
- Rule 2 operator_id NOT NULL — 3 атаки фин (3,4,9)
- Rule 5 immutable DO INSTEAD NOTHING — 2 атаки истории (5,10)
- Rule 3 v1 не удаляется — 1 атака цены (6)
- Rule 7 qr_code UNIQUE — 2 атаки QR (7,10)
- Rule 4 photo_url NOT NULL + 5 фото — 2 атаки фото (8,9)
- 14 исключений — потеряна 6 + перепутана 7 самые строгие
