# TASK_005 — Courier Flow — QR скан + 14 исключений + photo_url обязательно
Дата: 2026-11-04
SSOT: TASK_002 courier_exceptions 14, TASK_004 qr_scan Rule 7+5+4

## Поток курьера — App

### Список заказов OUT_FOR_DELIVERY
```
Заказ #123 QR-001 Платье
Адрес: Пермь Ленина 1 кв 2
Клиент: +7...
[Доставить] [Исключение]
```

### Скан QR — 3 типа

#### 1. PICKUP — забор
Кнопка [Сканировать QR забора]
- Сканирует QR-001 → проверка qr_code UNIQUE в items Rule 7
- Обязательно фото: [Сделать фото забора] photo_url NOT NULL Rule 4
- Если фото нет — кнопка [Подтвердить забор] disabled
- POST /api/transfer/scan {order_id, item_qr_code UNIQUE, photo_url NOT NULL, operator_id, type: PICKUP}
- Пишет transfer_history immutable Rule 5 + events TRANSFER_SCANNED idempotency_key UNIQUE

#### 2. RETURN — возврат клиенту
Кнопка [Сканировать QR возврата]
- Сканирует QR-001 → проверка Rule 7
- Обязательно фото возврата: photo_url NOT NULL Rule 4 — без него не закрыть CLOSED
- Клиент подтверждает: customer_confirmed
- POST /api/transfer/scan {type: RETURN, photo_url NOT NULL}
- Пишет return_confirmations photo_url NOT NULL Rule 4

#### 3. DAMAGE — повреждение/потеря — 14 исключений
Кнопка [Исключение] → список 14:
- 1 клиент не дома — фото двери обязательно
- 4 повреждена при заборе — фото повреждения обязательно
- 6 потеряна — фото пусто + DISPUTE + PAYMENT_REFUNDED operator_id Rule 2
- 7 перепутана — проверка qr_code UNIQUE Rule 7 — скан покажет не тот QR
- 11 упаковка повреждена — фото упаковки

Все требуют photo_url NOT NULL кроме потеряна — там DISPUTE + investigation

### 14 исключений — таблица для курьера

| # | Исключение | Кнопка | Что требует | Что пишет |
|---|---|---|---|---|
| 1 | клиент не дома | [Исключение 1] | фото двери photo_url NOT NULL | transfer_history + exception 1 + retry |
| 4 | повреждена при заборе | [Исключение 4] | фото повреждения photo_url NOT NULL | DISPUTE + investigation + events |
| 6 | потеряна | [Исключение 6] | — | DISPUTE + PAYMENT_REFUNDED operator_id Rule 2 + declared_value |
| 7 | перепутана | [Скан] | проверка qr_code UNIQUE Rule 7 | ошибка "QR не совпадает" |
| 9 | дверь не открыли | [Исключение 9] | фото двери | exception 9 + retry |

### Защита от дублей + immutable

- idempotency_key UNIQUE — курьер 2 раза сканирует — второй не вставится
- transfer_history immutable RULE DO INSTEAD NOTHING Rule 5 — нельзя подделать лог
- qr_code UNIQUE Rule 7 — только в items, не в orders

### UI правила

- Кнопка [Подтвердить] disabled пока нет photo_url NOT NULL — Rule 4
- Кнопка фин операции нет — только оператор Rule 2
- Фото обязательно для всех кроме потеряна — там DISPUTE
