# TASK_006 — Quality Gate — 5 фото этапов + чеклист 5 правил + idempotency_key
Дата: 2026-11-04
SSOT: TASK_001 DDL, TASK_002 8 шагов + 14 исключений, TASK_003 Price Lock, TASK_004 API 10, TASK_005 Frontend 24 состояния

## 5 фото этапов — обязательно для CLOSED Rule 4 + Rule 3

| # | Этап | Когда | Что фото | Куда пишет | Rule | Без фото? |
|---|---|---|---|---|---|---|
| 1 | Прием | NEW→ESTIMATED курьер забирает | Фото вещи при заборе + QR-001 | transfer_history photo_url NOT NULL + qr_code UNIQUE | Rule 7 QR только в items + Rule 4 photo_url NOT NULL + Rule 5 immutable | Не забрать — кнопка disabled |
| 2 | Дефектовка | ESTIMATED оператор оценивает | Фото дефекта + 5 этапов | estimates + price_versions snapshot price_version_id | Rule 3 v1 не удаляется snapshot + Rule 5 immutable events | Не оценить |
| 3 | До ремонта | IN_WORK мастер до | Фото до ремонта | events ESTIMATE_V1_CREATED + transfer_history | Rule 5 immutable + Rule 3 | Не в работу |
| 4 | После ремонта | READY мастер после | Фото после ремонта | events READY + quality gate | Quality Gate check | Не готово |
| 5 | Возврат | DELIVERED→CLOSED курьер возвращает | Фото возврата клиенту + customer_confirmed | return_confirmations photo_url NOT NULL + events DELIVERED→CLOSED | Rule 4 photo_url NOT NULL + customer_confirmed + operator_id Rule 2 + idempotency_key | Не закрыть — кнопка Списать disabled |

Все 5 фото NOT NULL кроме потеряна исключение 6 — там DISPUTE + PAYMENT_REFUNDED

## Quality Gate — чеклист 6 пунктов перед CLOSED

```
[ ] 1. 5 фото есть? — 5 photo_url NOT NULL — без фото не CLOSED Rule 4
[ ] 2. QR совпадает? — items.qr_code UNIQUE проверка Rule 7 — вещь, не заказ, перепутана 7 ошибка
[ ] 3. Цена зафиксирована? — price_version_id snapshot + v1 не удаляется Rule 3 — даже если прайс поменялся
[ ] 4. operator_id есть для фина? — payments.operator_id NOT NULL Rule 2 AI не допущен — без оператора 403
[ ] 5. events + transfer_history immutable? — RULE DO INSTEAD NOTHING Rule 5 — нельзя DELETE/UPDATE — аудит
[ ] 6. idempotency_key защита? — events.idempotency_key UNIQUE NOT NULL — дубль Согласен/Скан/Списать не спишет 2 раза — duplicate key → "Уже обработано"
```

Только если все 6 галочек — кнопка [Списать] → CLOSED активна

## Таблица Quality Gate по API

| API | Что проверяет | Rule |
|---|---|---|
| POST /api/order/estimate | snapshot price_version_id + v1 не удаляется + фото дефекта | Rule 3 + Rule 5 |
| POST /api/telegram/callback agree | idempotency_key UNIQUE {order_id}:CUSTOMER_AGREED:timestamp:random + Согласен | idempotency_key + Rule 5 |
| POST /api/payment/hold | operator_id NOT NULL Rule 2 + idempotency_key UNIQUE | Rule 2 + idempotency |
| POST /api/transfer/scan PICKUP | qr_code UNIQUE в items Rule 7 + photo_url NOT NULL Rule 4 + transfer_history immutable Rule 5 + idempotency_key | Rule 7+4+5+idemp |
| POST /api/transfer/scan RETURN | photo_url NOT NULL Rule 4 + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed | Rule 4 |
| POST /api/payment/capture | operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + 5 фото + idempotency_key | Rule 2+4+idemp |
| POST /api/payment/refund | operator_id NOT NULL Rule 2 + reason + исключение 6 declared_value | Rule 2 |

## 14 исключений — Quality Gate

| # | Исключение | Фото? | Что в Quality Gate | Платеж |
|---|---|---|---|---|
| 1 | клиент не дома | фото двери photo_url NOT NULL | retry | HOLD остается |
| 4 | повреждена при заборе | фото повреждения NOT NULL | DISPUTE + investigation | REFUND operator_id |
| 6 | потеряна | — | DISPUTE + investigation + declared_value | REFUND operator_id + declared_value Rule 2 |
| 7 | перепутана | проверка qr_code UNIQUE Rule 7 | ошибка QR не совпадает | HOLD остается |
| 11 | упаковка повреждена | фото упаковки NOT NULL | DISPUTE | REFUND |

## Итого

5 фото = 5 photo_url NOT NULL + 5 правил Конституции + idempotency_key UNIQUE + qr_code UNIQUE + operator_id NOT NULL = нельзя закрыть без аудита
