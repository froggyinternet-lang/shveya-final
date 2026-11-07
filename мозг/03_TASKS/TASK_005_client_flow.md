# TASK_005 — Client Flow — Telegram NEW→CLOSED + Согласен/Отказываюсь
Дата: 2026-11-04
SSOT: TASK_002 State Machine, TASK_004 Telegram Buttons idempotency_key

## Поток клиента Telegram — 8 шагов

### 1. NEW — Заказ создан
Сообщение:
```
🧵 Заказ #123 QR-001 создан
Вещь: Платье
Статус: Ожидает оценки
```
UI: кнопка [Отменить заказ] → CANCELLED

### 2. ESTIMATED v1 — Оценка готова + фото 5 этапов Rule 3
Сообщение:
```
🧵 Оценка готова v1
Вещь: Платье QR-001
Цена: 1000 руб
Фото: [5 этапов]
Дефект: ...

[✅ Согласен v1] [❌ Отказываюсь]
```
callback_data: agree:{order_id}:1 / reject:{order_id}:1
idempotency_key: {order_id}:CUSTOMER_AGREED:timestamp:random UNIQUE
Защита: второй клик падает duplicate key, показывает "Уже обработано"

### 3. AGREED — Согласен + HOLD с operator_id Rule 2
Сообщение:
```
✅ Согласен v1 принят
Оплата захолдирована 1000 руб
В работе
```
Backend: POST /api/payment/hold operator_id NOT NULL Rule 2 + events CUSTOMER_AGREED idempotency_key UNIQUE + AGREED

### 4. IN_WORK — В работе у мастера
Сообщение: "В работе у мастера"
Если доп дефект:
```
⚠️ Найден доп дефект
Новая оценка v2 1200 руб
v1 остается — аудит Rule 3
Фото доп дефекта: ...

[✅ Согласен v2] [❌ Отказываюсь v2]
```
v1 не удаляется — история версий

### 5. READY — Готово
Сообщение: "Готово, ждите курьера"

### 6. OUT_FOR_DELIVERY — Курьер везет
Сообщение:
```
🚚 Курьер везет
Курьер: Иван +7...
```
Трекинг + кнопка [Связаться]

### 7. DELIVERED — Доставлено + фото возврата Rule 4
Сообщение:
```
📦 Доставлено
Фото возврата: [фото]
[✅ Подтвердить возврат] [❌ Спор]
```
Подтвердить → пишет return_confirmations photo_url NOT NULL + customer_confirmed Rule 4 → CLOSED
Спор → DISPUTE + фото повреждения обязательно

### 8. CLOSED — Закрыт
Сообщение:
```
✅ Заказ закрыт
Чек: 1000 руб списан
Спасибо!
```
Требует: return_confirmations photo_url NOT NULL Rule 4 + PAYMENT_CAPTURED operator_id Rule 2 + customer_confirmed

### CANCELLED / DISPUTE
- CANCELLED: "Отменен" + причина + возврат денег PAYMENT_REFUNDED operator_id Rule 2
- DISPUTE: "Спор, investigation" + PAYMENT_REFUNDED declared_value если потеряна исключение 6

## Конституция в UI клиента

- Rule 2: клиент не видит operator_id, но платеж без него не пройдет — защита
- Rule 3: v1 не удаляется, клиент видит историю v1,v2
- Rule 4: без фото возврата не закрыть — кнопка Подтвердить требует photo_url
- Rule 5: клиент не может удалить историю — immutable
- Rule 7: QR показывается как QR-001 из items.qr_code UNIQUE

## Защита от дублей

- idempotency_key UNIQUE — второй клик Согласен не спишет деньги 2 раза
- База: events.idempotency_key UNIQUE NOT NULL
