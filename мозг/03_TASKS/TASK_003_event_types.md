# TASK_003 — Event Types — 12 типов событий + idempotency_key формат
Дата: 2026-11-04
SSOT: TASK_001 events DDL, TASK_002 State Machine

## Формат idempotency_key

```
{order_id}:{event_type}:{ISO8601}:{random4}
```

Пример:
```
550e8400-e29b-41d4-a716-446655440000:CUSTOMER_AGREED:2026-11-04T21:15:00:ab12
```

Защита:
- UNIQUE NOT NULL — база не даст вставить дубль
- Если клиент 2 раза жмет Согласен — второй INSERT упадет с duplicate key
- Никакого двойного списания

## 12 типов событий — связь с State Machine + Конституцией

| # | event_type | Когда создается | State Machine переход | Требует | Конституция |
|---|---|---|---|---|---|
| 1 | ORDER_CREATED | NEW заказ создан | [*]→NEW | items с qr_code UNIQUE | Rule 7 QR только в items |
| 2 | ESTIMATE_V1_CREATED | Мастер оценил, фото 5 этапов | NEW→ESTIMATED | price_version_id snapshot, photo_url | Rule 3 цена через версию |
| 3 | ESTIMATE_V2_CREATED | Доп дефект найден | IN_WORK→оценка v2 | старая v1 не удаляется | Rule 3 v1 не удаляется |
| 4 | CUSTOMER_AGREED | Клиент нажал Согласен | ESTIMATED→AGREED | estimate AGREED + idempotency_key | Защита от дублей |
| 5 | CUSTOMER_REJECTED | Клиент нажал Отказываюсь | ESTIMATED→CANCELLED | — | — |
| 6 | TRANSFER_SCANNED | QR сканирован при заборе/возврате | AGREED→IN_WORK, READY→OUT_FOR_DELIVERY | qr_code, photo_url в transfer_history | Rule 7 + Rule 5 immutable |
| 7 | PAYMENT_HOLD | Деньги зарезервированы | AGREED→IN_WORK | operator_id NOT NULL | Rule 2 AI не допущен к фину |
| 8 | PAYMENT_CAPTURED | Деньги списаны после DELIVERED | DELIVERED→CLOSED | operator_id + return_confirmations | Rule 2 + Rule 4 |
| 9 | PAYMENT_REFUNDED | Возврат денег при CANCELLED/DISPUTE | →CANCELLED | operator_id NOT NULL | Rule 2 |
| 10 | RETURN_CONFIRMED | Возврат подтвержден фото | OUT_FOR_DELIVERY→DELIVERED→CLOSED | photo_url NOT NULL в return_confirmations | Rule 4 без фото не закрыть |
| 11 | CANCELLED | Заказ отменен (любое исключение) | →CANCELLED | operator_id если фин, transfer_history | Rule 2 + Rule 5 |
| 12 | DISPUTE | Спор (потеряна/повреждена) | DELIVERED→DISPUTE | operator_id + investigation | Rule 2 + Rule 5 |

## Пример потока заказа — все события

```
ORDER_CREATED (Rule 7 qr_code)
→ ESTIMATE_V1_CREATED (Rule 3 price_versions)
→ CUSTOMER_AGREED (idempotency_key UNIQUE)
→ PAYMENT_HOLD (Rule 2 operator_id)
→ TRANSFER_SCANNED забор (Rule 5 immutable + Rule 7)
→ (опционально ESTIMATE_V2_CREATED если доп дефект)
→ TRANSFER_SCANNED готовность
→ TRANSFER_SCANNED выдача курьеру
→ RETURN_CONFIRMED возврат (Rule 4 photo_url)
→ PAYMENT_CAPTURED (Rule 2 operator_id)
→ CLOSED
```

## Immutable — нельзя подделать

```sql
CREATE RULE no_update_events AS ON UPDATE TO events DO INSTEAD NOTHING;
CREATE RULE no_delete_events AS ON DELETE TO events DO INSTEAD NOTHING;
```

- events как transfer_history — нельзя UPDATE/DELETE
- Аудит 100% — все действия в логе
- Даже если хак — лог не удалить

## Связь с 14 исключениями курьера (TASK_002)

- Исключение 4,6,7 → TRANSFER_SCANNED с фото повреждения + CANCELLED/DISPUTE
- Исключение 5,13 → CUSTOMER_REJECTED + CANCELLED
- Исключение 6 потеряна → DISPUTE + PAYMENT_REFUNDED с operator_id
- Все пишут в events + transfer_history с photo_url
