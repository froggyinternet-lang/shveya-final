# TASK_007 — Security Checklist — 7 пунктов Constitution + 10 атак
Дата: 2026-11-04
SSOT: SHVEYA.md v2.3 + TASK_007_anti_fraud 10 атак

## Security Checklist — 7 пунктов — все должны быть галочками перед MVP Launch

```
[ ] 1. Rule 2: AI не допущен — operator_id NOT NULL для всех фин операций
     - Проверка: payments.operator_id UUID NOT NULL
     - API: POST /api/payment/hold {operator_id NOT NULL} → 403 если нет
           POST /api/payment/capture {operator_id NOT NULL} → 403 если нет
           POST /api/payment/refund {operator_id NOT NULL} → 403 если нет
     - Frontend: [Захолдить][Списать][Возврат] disabled пока нет operator_id
               Текст: "Выберите оператора — Rule 2 AI не допущен"
     - Атаки закрывает: 3 Дубль Списать, 4 Подделка operator_id, 9 Потеряна без возврата
     - Тест: вызвать HOLD без operator_id → 403 Forbidden

[ ] 2. Rule 5: immutable — нельзя DELETE/UPDATE — RULE DO INSTEAD NOTHING
     - Проверка: CREATE RULE no_update AS ON UPDATE TO events DO INSTEAD NOTHING
               CREATE RULE no_delete AS ON DELETE TO events DO INSTEAD NOTHING
               То же для transfer_history
               REVOKE UPDATE, DELETE ON events, transfer_history FROM public, courier, client
     - API: любой UPDATE/DELETE → DO INSTEAD NOTHING — ничего не удалится
     - Frontend: Dashboard events + transfer_history только просмотр — нет кнопок удалить/изменить
     - Атаки закрывает: 5 Подделка истории, 10 Перепутана без проверки (лог не подделать)
     - Тест: DELETE FROM events WHERE id=... → 0 rows — RULE срабатывает

[ ] 3. idempotency_key UNIQUE — защита от дублей
     - Проверка: events.idempotency_key TEXT UNIQUE NOT NULL
               idempotency_key = {order_id}:{event_type}:{timestamp}:{random}
               Согласен: {order_id}:CUSTOMER_AGREED:{version}:{timestamp}:{random}
               Скан: {order_id}:TRANSFER_SCANNED:{qr_code}:{timestamp}:{random}
               Списать: {order_id}:PAYMENT_CAPTURED:{amount}:{timestamp}:{random}
               Холд: {order_id}:PAYMENT_HOLD:{amount}:{timestamp}:{random}
               Рефанд: {order_id}:PAYMENT_REFUNDED:{amount}:{timestamp}:{random}
     - API: второй INSERT с тем же idempotency_key → duplicate key violation UNIQUE → "Уже обработано" — деньги не списываются 2 раза
     - Frontend: Telegram второй клик Согласен → "Уже обработано" — Courier второй скан → "Уже обработано" — Operator второй Списать → "Уже обработано"
     - Атаки закрывает: 1 Дубль Согласен, 2 Дубль QR скан, 3 Дубль Списать
     - Тест: 2 раза вызвать agree с одним idempotency_key → второй 409 Conflict "Уже обработано"

[ ] 4. Rule 7: QR только в items — qr_code UNIQUE NOT NULL — вещь, не заказ
     - Проверка: items(qr_code VARCHAR UNIQUE NOT NULL) — orders без qr_code
               CREATE UNIQUE INDEX ON items(qr_code)
     - API: POST /api/order/create создает qr_code в items, не в orders
           POST /api/transfer/scan проверяет items.qr_code UNIQUE — если не совпадает → 400 "QR не совпадает — перепутана 7"
     - Frontend: Courier скан проверяет UNIQUE в items Rule 7 — перепутана 7 ошибка
     - Атаки закрывает: 7 QR в orders, 10 Перепутана без проверки
     - Тест: вставить 2 items с одним qr_code → duplicate key UNIQUE — нельзя

[ ] 5. Rule 4: photo_url NOT NULL — без фото не закрыть + 5 фото этапов
     - Проверка: transfer_history(photo_url TEXT NOT NULL) — PICKUP/RETURN/DAMAGE все требуют фото кроме потеряна 6
               return_confirmations(photo_url TEXT NOT NULL, customer_confirmed BOOL) — без фото не CLOSED
               5 фото этапов: Прием + Дефектовка + До ремонта + После ремонта + Возврат — все NOT NULL
     - API: POST /api/transfer/scan {photo_url NOT NULL} → 400 если нет — кроме исключение 6 потеряна
           POST /api/payment/capture требует return_confirmations photo_url NOT NULL + 5 фото + Quality Gate 6 чеков
     - Frontend: Courier [Подтвердить] disabled пока нет photo_url NOT NULL — Operator [Списать] disabled пока нет return_confirmations + 5 фото
               Текст: "Нет фото возврата — Rule 4" — "Нет фото забора — Rule 4"
     - Атаки закрывает: 8 Закрытие без фото, 9 Потеряна без возврата (фото если есть)
     - Тест: вызвать RETURN без photo_url → 400 photo_url NOT NULL — нельзя закрыть

[ ] 6. Rule 3: v1 не удаляется — Price Lock — immutable price_versions
     - Проверка: price_versions(id, version, price, created_at) immutable — нельзя DELETE/UPDATE — только INSERT новой версии
               estimates(price_version_id UUID REFERENCES price_versions, version INT) — snapshot — v1 остается аудит
               v1 1000 → v2 1200 — история версий — v1 не удаляется
     - API: POST /api/order/estimate создает новую версию, старая не удаляется — ESTIMATE_V1_CREATED, ESTIMATE_V2_CREATED
           Клиент видит историю v1,v2,v3 + snapshot price_version_id
     - Frontend: карточка показывает историю v1,v2,v3 — даже если прайс поменялся, у заказа старый snapshot
     - Атаки закрывает: 6 Смена цены без версии
     - Тест: UPDATE price_versions SET price=9999 WHERE version=1 → DO INSTEAD NOTHING — нельзя — только INSERT v2

[ ] 7. 14 исключений + 5 фото + Quality Gate 6 чеков + declared_value
     - Проверка: 14 исключений курьера — все требуют photo_url NOT NULL кроме потеряна 6
               6 потеряна → DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id NOT NULL Rule 2 — самая строгая
               7 перепутана → qr_code UNIQUE проверка Rule 7 → ошибка "QR не совпадает"
               4 повреждена при заборе → фото повреждения NOT NULL → DISPUTE + investigation + REFUND operator_id
               11 упаковка повреждена → фото упаковки NOT NULL → DISPUTE
               Quality Gate 6 чеков: 5 фото? QR? Цена? operator_id? immutable? idempotency_key?
     - API: POST /api/transfer/scan исключение — {exception_id, photo_url NOT NULL (кроме 6), qr_code, idempotency_key}
           POST /api/payment/refund {amount=declared_value если потеряна 6, operator_id NOT NULL, reason}
     - Frontend: Courier [Исключение] → выбрать из 14 — все требуют фото кроме потеряна — [Подтвердить] disabled без фото Rule 4
               Operator [Возврат денег] требует operator_id NOT NULL Rule 2 + для потеряна 6 — возврат declared_value
     - Атаки закрывает: 9 Потеряна, 10 Перепутана, 4 повреждена, 11 упаковка
     - Тест: вызвать потеряна 6 без operator_id → 403 — без operator_id нельзя вернуть declared_value
```

## Итого 7 пунктов = 10 атак закрыты

| Пункт | Rule | Атаки |
|---|---|---|
| 1 operator_id | Rule 2 | 3,4,9 |
| 2 immutable | Rule 5 | 5,10 |
| 3 idempotency_key | UNIQUE | 1,2,3 |
| 4 qr_code UNIQUE | Rule 7 | 7,10 |
| 5 photo_url NOT NULL | Rule 4 + 5 фото | 8,9 |
| 6 v1 не удаляется | Rule 3 | 6 |
| 7 14 исключений + declared_value | 6,7,4,11 | 9,10 |

Все 7 галочек — можно в MVP Launch
