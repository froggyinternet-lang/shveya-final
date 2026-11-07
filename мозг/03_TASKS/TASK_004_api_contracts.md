# TASK_004 — API Contracts — 10 эндпоинтов + 6 колонок + Конституция
Дата: 2026-11-04
SSOT: TASK_001 DDL, TASK_002 State Machine, TASK_003 Event Log

## Таблица 10 эндпоинтов — 6 колонок: метод / путь / вход / выход / Rule / исключение

| # | Метод | Путь | Вход | Выход | Rule Конституции | Исключение курьера |
|---|---|---|---|---|---|---|
| 1 | POST | /api/telegram/callback | {callback_data: agree:{order_id}:{v}, idempotency_key UNIQUE, order_id} | {event: CUSTOMER_AGREED, estimate: AGREED} | Rule 3 price_version snapshot, защита от дублей idempotency_key | — |
| 2 | POST | /api/telegram/callback | {callback_data: reject:{order_id}:{v}, idempotency_key} | {event: CUSTOMER_REJECTED, order: CANCELLED} | Rule 5 immutable events | Исключение 5,13 клиент отказался |
| 3 | POST | /api/transfer/scan | {order_id, item_qr_code UNIQUE, photo_url NOT NULL, operator_id, type: PICKUP} | {transfer_history: created, event: TRANSFER_SCANNED} | Rule 7 qr_code только в items + Rule 5 immutable + Rule 4 photo_url | Исключение 4 повреждена при заборе, 7 перепутана |
| 4 | POST | /api/transfer/scan | {order_id, item_qr_code, photo_url NOT NULL, operator_id, type: RETURN} | {transfer_history: created, event: RETURN_CONFIRMED} | Rule 4 return_confirmations photo_url NOT NULL, Rule 5 | Исключение 1,9 клиент не дома/дверь |
| 5 | POST | /api/transfer/scan | {order_id, item_qr_code, photo_url NOT NULL, type: DAMAGE} | {event: DISPUTE, order: DISPUTE, investigation} | Rule 7 + Rule 5 immutable + photo_url обязательно | Исключение 6 потеряна, 11 упаковка повреждена |
| 6 | POST | /api/payment/hold | {order_id, amount, operator_id NOT NULL, idempotency_key UNIQUE} | {payment: HOLD, event: PAYMENT_HOLD} | Rule 2 AI не допущен — только с operator_id | — |
| 7 | POST | /api/payment/capture | {order_id, operator_id NOT NULL, return_confirmations_id, idempotency_key} | {payment: CAPTURED, order: CLOSED, event: PAYMENT_CAPTURED} | Rule 2 operator_id + Rule 4 return_confirmations photo_url NOT NULL + customer_confirmed | Исключение 13 вернуть без ремонта — только через return_confirmations |
| 8 | POST | /api/payment/refund | {order_id, operator_id NOT NULL, reason, idempotency_key} | {payment: REFUNDED, order: CANCELLED, event: PAYMENT_REFUNDED} | Rule 2 operator_id обязателен для возврата денег | Исключение 6 потеряна → возврат declared_value |
| 9 | POST | /api/order/create | {items: [{qr_code UNIQUE}], customer_id, price_version_id snapshot} | {order: NEW, items: created, event: ORDER_CREATED} | Rule 7 QR только в items + Rule 3 snapshot | Исключение 2 адрес не найден |
| 10 | POST | /api/order/estimate | {item_id, price_version_id, version INT (1,2), price, photo_url, operator_id} | {estimate: CREATED, event: ESTIMATE_V1/V2_CREATED, telegram: sent} | Rule 3 v1 не удаляется, создается v2 + Rule 5 immutable | Исключение 3 вещь не готова, 10 фото не прошло Quality Gate |

## Детали каждого API — как вшивает Конституцию

### Telegram callback (1,2) — защита от дублей
```json
// Вход
{
  "callback_data": "agree:550e8400-e29b-41d4-a716-446655440000:1",
  "idempotency_key": "550e8400:CUSTOMER_AGREED:2026-11-04T21:00:00:ab12",
  "telegram_user_id": "123456"
}
// Если дубль — база вернет duplicate key error на idempotency_key UNIQUE
// Деньги не спишутся 2 раза
```

### Transfer scan (3,4,5) — immutable + photo_url
```json
{
  "order_id": "uuid",
  "item_qr_code": "QR-001-UNIQUE", // проверка UNIQUE в items
  "photo_url": "https://... NOT NULL", // обязательно
  "operator_id": "uuid оператора",
  "type": "PICKUP|RETURN|DAMAGE",
  "location": "пункт/клиент"
}
// Пишет сразу 2 таблицы: transfer_history immutable + events с idempotency_key
// Без фото не вставит — Rule 4 + Rule 5
```

### Payment (6,7,8) — operator_id обязателен Rule 2
```json
{
  "order_id": "uuid",
  "operator_id": "uuid NOT NULL — Rule 2 AI не допущен",
  "amount": 1000,
  "idempotency_key": "order_id:PAYMENT_HOLD:timestamp:random UNIQUE"
}
// Без operator_id — 403 Forbidden
// capture требует return_confirmations photo_url NOT NULL + customer_confirmed — Rule 4
```

## Связь с State Machine 002

- /order/create → [*]→NEW → пишет ORDER_CREATED
- /order/estimate → NEW→ESTIMATED → ESTIMATE_V1_CREATED
- /telegram/callback agree → ESTIMATED→AGREED → CUSTOMER_AGREED
- /payment/hold → AGREED→IN_WORK → PAYMENT_HOLD + TRANSFER_SCANNED
- /transfer/scan PICKUP → IN_WORK (мастер готов) → TRANSFER_SCANNED
- /transfer/scan RETURN → OUT_FOR_DELIVERY→DELIVERED → RETURN_CONFIRMED
- /payment/capture → DELIVERED→CLOSED → требует return_confirmations photo_url NOT NULL (Rule 4)
- /payment/refund → →CANCELLED/DISPUTE → требует operator_id (Rule 2)

## Все API пишут в 2 места

1. events с idempotency_key UNIQUE NOT NULL — защита от дублей
2. transfer_history immutable RULE DO INSTEAD NOTHING — аудит

Нельзя подделать — нельзя UPDATE/DELETE
