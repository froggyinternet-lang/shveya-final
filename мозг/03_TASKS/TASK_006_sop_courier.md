# TASK_006 — SOP Courier — QR скан + photo_url обязательно + 14 исключений
Дата: 2026-11-04

## SOP Курьера App — 3 типа скана + 14 исключений

### Правила — Constitution

- Rule 7: QR только в items.qr_code UNIQUE — не в orders — вещь, не заказ
- Rule 4: photo_url NOT NULL обязательно для всех сканов кроме потеряна исключение 6
- Rule 5: transfer_history immutable RULE DO INSTEAD NOTHING — нельзя подделать лог
- Rule 2: фин операций нет — только оператор
- idempotency_key UNIQUE — второй скан не вставится

### Скан 1: PICKUP — забор из ателье

1. Открыть задачу OUT_FOR_DELIVERY? Нет — READY→OUT_FOR_DELIVERY забор
2. Нажать [Сканировать QR забора]
3. Сканировать QR-001 → проверка qr_code UNIQUE в items Rule 7
4. Если QR не совпадает → ошибка "QR не совпадает — перепутана 7"
5. Сделать фото забора — [Сделать фото] photo_url NOT NULL Rule 4 обязательно
6. Кнопка [Подтвердить забор] disabled пока нет фото — Rule 4
7. Нажать [Подтвердить] → POST /api/transfer/scan PICKUP {qr_code UNIQUE, photo_url NOT NULL, idempotency_key}
8. Пишет transfer_history immutable + events TRANSFER_SCANNED
9. Второй скан — idempotency_key защита — "Уже обработано"

### Скан 2: RETURN — возврат клиенту

1. Список доставки OUT_FOR_DELIVERY Заказ #123 QR-001 адрес
2. Нажать [Доставлено] → [Сканировать QR возврата]
3. Сканировать QR-001 → проверка Rule 7
4. Сделать фото возврата — photo_url NOT NULL Rule 4 обязательно — без него не закрыть CLOSED
5. Клиент подтверждает customer_confirmed
6. Нажать [Подтвердить возврат] → POST /api/transfer/scan RETURN photo_url NOT NULL
7. Пишет return_confirmations photo_url NOT NULL Rule 4
8. Оператор потом спишет с operator_id Rule 2

### Скан 3: DAMAGE — 14 исключений — фото обязательно

Нажать [Исключение] → выбрать из 14:

| # | Исключение | Что делать | Фото? | Что пишет |
|---|---|---|---|---|
| 1 | клиент не дома | фото двери подъезда + звонок клиенту | photo_url NOT NULL двери | transfer_history + exception 1 + retry завтра |
| 2 | адрес неверный | фото адреса | photo_url NOT NULL | exception 2 |
| 3 | клиент перенес | фото чата | photo_url NOT NULL | exception 3 + reschedule |
| 4 | повреждена при заборе | фото повреждения крупно | photo_url NOT NULL обязательно | DISPUTE + investigation + events DAMAGE + PAYMENT_REFUNDED operator_id |
| 5 | клиент отказался при доставке | фото вещи + отказ | photo_url NOT NULL | CANCELLED + REFUND operator_id Rule 2 |
| 6 | потеряна | — ничего нет | — | DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id Rule 2 — самая строгая |
| 7 | перепутана | скан QR — проверка UNIQUE Rule 7 | — | ошибка "QR не совпадает" — не тот QR |
| 8 | курьер опоздал | фото времени | photo_url | exception 8 |
| 9 | дверь не открыли | фото двери 2 раза с интервалом | photo_url NOT NULL двери | exception 9 |
| 10 | клиент не отвечает | фото звонков скрин | photo_url | exception 10 + retry |
| 11 | упаковка повреждена | фото упаковки | photo_url NOT NULL упаковки | DISPUTE + investigation + фото Rule 4 |
| 12 | вещь грязная после ремонта | фото грязи | photo_url NOT NULL | DISPUTE + return в ателье |
| 13 | клиент передумал | фото вещи | photo_url NOT NULL | CANCELLED 13 + REFUND operator_id |
| 14 | форс-мажор | фото ситуации | photo_url | exception 14 + investigation |

Все требуют photo_url NOT NULL кроме 6 потеряна — там DISPUTE + investigation + возврат declared_value

### Защита

- Кнопка [Подтвердить] disabled пока нет photo_url NOT NULL Rule 4
- transfer_history immutable Rule 5 — нельзя подделать — RULE DO INSTEAD NOTHING
- qr_code UNIQUE Rule 7 — только в items
- idempotency_key UNIQUE — второй скан не вставится
