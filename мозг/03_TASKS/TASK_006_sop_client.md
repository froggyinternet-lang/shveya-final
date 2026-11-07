# TASK_006 — SOP Client — Telegram Согласен/Отказываюсь + защита от дублей
Дата: 2026-11-04

## SOP Клиента Telegram — NEW→CLOSED

### Шаг 1: NEW — заказ создан
Сообщение:
```
🧵 Заказ #123 QR-001 создан
Вещь: Платье
Статус: Ожидает оценки
```
Кнопка: [Отменить заказ] → CANCELLED исключение 5

### Шаг 2: ESTIMATED v1 — оценка + фото 5 этапов + кнопки Согласен/Отказываюсь Rule 3
Сообщение:
```
🧵 Оценка готова v1
Вещь: Платье QR-001
Цена: 1000 руб
Фото: [5 этапов до/дефект]
Дефект: пятно

[✅ Согласен v1] [❌ Отказываюсь]
```
callback_data: agree:123:1 / reject:123:1
idempotency_key: 123:CUSTOMER_AGREED:2026-11-04T21:30:00:ab12 UNIQUE
Защита: второй клик падает duplicate key UNIQUE → "Уже обработано" — деньги не спишутся 2 раза
v1 не удаляется Rule 3 — остается в истории даже если создадут v2

### Шаг 3: AGREED — согласен + HOLD operator_id Rule 2
Сообщение:
```
✅ Согласен v1 принят
Оплата захолдирована 1000 руб
В работе у мастера
```
Backend: PAYMENT_HOLD требует operator_id NOT NULL Rule 2 — без оператора 403 — AI не допущен

### Шаг 4: IN_WORK — в работе + доп дефект v2 Rule 3
Сообщение "В работе у мастера" + прогресс
Если доп дефект:
```
⚠️ Найден доп дефект
Новая оценка v2 1200 руб
v1 1000 остается — аудит Rule 3
Фото доп дефекта: ...

[✅ Согласен v2] [❌ Отказываюсь v2]
```
v1 не удаляется — история версий v1,v2

### Шаг 5: READY — готово
Сообщение: "Готово, ждите курьера"

### Шаг 6: OUT_FOR_DELIVERY — курьер везет
Сообщение:
```
🚚 Курьер везет
Курьер: Иван +7...
[Связаться]
```
Трекинг

### Шаг 7: DELIVERED — доставлено + фото возврата Rule 4
Сообщение:
```
📦 Доставлено
Фото возврата: [фото]
[✅ Подтвердить возврат] [❌ Спор — повреждена]
```
Подтвердить → пишет return_confirmations photo_url NOT NULL + customer_confirmed Rule 4 → CLOSED
Спор → DISPUTE + фото повреждения обязательно Rule 4 + investigation + PAYMENT_REFUNDED operator_id Rule 2 если потеряна исключение 6 declared_value

### Шаг 8: CLOSED — закрыт + чек
Сообщение:
```
✅ Заказ закрыт
Чек: 1000 руб списан
Спасибо!
Фото 5 этапов сохранены
```
Требует: return_confirmations photo_url NOT NULL Rule 4 + PAYMENT_CAPTURED operator_id Rule 2 + customer_confirmed + 5 фото + idempotency_key

### CANCELLED / DISPUTE
- CANCELLED 5,13 клиент отказался → "Отменен" + причина + возврат денег PAYMENT_REFUNDED operator_id Rule 2
- DISPUTE 4,6,7,11 → "Спор, investigation" + фото повреждения Rule 4 + возврат declared_value если потеряна 6 + operator_id Rule 2

### Constitution в клиенте
- Rule 2: клиент не видит operator_id, но платеж без него не пройдет — защита AI не допущен
- Rule 3: v1 не удаляется — видит историю v1,v2
- Rule 4: без фото возврата не закрыть — кнопка Подтвердить требует photo_url
- Rule 5: не может удалить историю — immutable
- Rule 7: QR показывается как QR-001 из items.qr_code UNIQUE — вещь, не заказ

### Защита от дублей
- idempotency_key UNIQUE — второй клик Согласен не спишет деньги 2 раза — база events.idempotency_key UNIQUE NOT NULL
- Второй клик — duplicate key → "Уже обработано"
