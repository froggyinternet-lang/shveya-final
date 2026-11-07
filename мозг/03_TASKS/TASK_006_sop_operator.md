# TASK_006 — SOP Operator — 8 шагов + 14 исключений + фото обязательно
Дата: 2026-11-04
SSOT: TASK_002 8 шагов, TASK_004 API 10, TASK_006 Quality Gate 5 фото

## SOP Оператора Dashboard — 8 шагов NEW→CLOSED

### Шаг 1: NEW → ESTIMATED — создать оценку v1
- Открыть заказ #123 QR-001
- Сделать 2 фото: дефектовка + 5 этапов
- Создать estimate v1 + snapshot price_version_id Rule 3 — v1 не удаляется
- API: POST /api/order/estimate {order_id, price_version_id snapshot, photos}
- Пишет: estimates version=1 + events ESTIMATE_V1_CREATED + transfer_history immutable Rule 5

### Шаг 2: ESTIMATED → AGREED/CANCELLED — отправить клиенту Telegram
- Кнопка [Отправить клиенту]
- Клиент видит фото 5 этапов + цена 1000 v1 + [✅ Согласен v1][❌ Отказываюсь]
- callback_data agree:{order_id}:1 / reject:{order_id}:1
- idempotency_key UNIQUE защита от дублей — второй клик "Уже обработано"
- Если Согласен → CUSTOMER_AGREED + AGREED, если Отказываюсь → CANCELLED исключение 5,13

### Шаг 3: AGREED → IN_WORK — захолдить платеж Rule 2
- Кнопка [Захолдить платеж] disabled пока нет operator_id NOT NULL Rule 2
- Выбрать оператора в dropdown — Rule 2 AI не допущен
- API: POST /api/payment/hold {order_id, amount, operator_id NOT NULL, idempotency_key UNIQUE}
- Без operator_id — 403 Forbidden
- Пишет: payments operator_id + PAYMENT_HOLD + transfer_history

### Шаг 4: IN_WORK → READY — если доп дефект → v2 Rule 3
- Если мастер нашел доп дефект:
  - Фото доп дефекта обязательно
  - Кнопка [Создать v2] — v1 не удаляется, создается v2 рядом Rule 3
  - История: v1 1000 → v2 1200 snapshot
  - Отправить клиенту снова [Согласен v2][Отказываюсь v2]
- API: POST /api/order/estimate v2 ESTIMATE_V2_CREATED
- БД: price_versions immutable, estimates version 2, старая не удаляется

### Шаг 5: READY → OUT_FOR_DELIVERY — выдать курьеру Rule 7+4+5
- Кнопка [Выдать курьеру]
- Курьер сканирует QR-001 → проверка qr_code UNIQUE в items Rule 7
- Фото забора photo_url NOT NULL обязательно Rule 4
- transfer_history immutable RULE DO INSTEAD NOTHING Rule 5
- API: POST /api/transfer/scan PICKUP {qr_code UNIQUE, photo_url NOT NULL, operator_id, idempotency_key}
- idempotency_key защита — второй скан не вставится

### Шаг 6: OUT_FOR_DELIVERY → DELIVERED — трекинг + 14 исключений
- Трекинг курьера
- Курьер: [Доставлено] или [Исключение]
- 14 исключений — все требуют фото кроме потеряна:
  - 1 клиент не дома → фото двери + retry
  - 4 повреждена при заборе → фото повреждения + DISPUTE
  - 6 потеряна → DISPUTE + PAYMENT_REFUNDED operator_id + declared_value
  - 7 перепутана → ошибка qr_code UNIQUE не совпадает Rule 7
  - 11 упаковка повреждена → фото упаковки + DISPUTE
- Курьер кнопка [Подтвердить] disabled пока нет photo_url NOT NULL Rule 4

### Шаг 7: DELIVERED → CLOSED — фото возврата Rule 4 + operator_id Rule 2
- Фото возврата обязательно return_confirmations photo_url NOT NULL Rule 4
- customer_confirmed — клиент подтверждает
- Кнопка [Списать] disabled пока нет:
  - return_confirmations photo_url NOT NULL Rule 4
  - operator_id NOT NULL Rule 2
  - 5 фото этапов
  - 6 чеков Quality Gate
- API: POST /api/payment/capture {order_id, operator_id NOT NULL, return_confirmations_id, idempotency_key}
- Без фото — "Нет фото возврата — Rule 4"
- Без operator_id — "Выберите оператора — Rule 2"

### Шаг 8: CLOSED — архив
- Чек списан
- Просмотр истории v1,v2,v3 + events + transfer_history immutable — нельзя DELETE/UPDATE Rule 5
- 5 фото этапов сохранены

### CANCELLED / DISPUTE — исключения
- CANCELLED 5,13 клиент отказался → [Возврат денег] PAYMENT_REFUNDED operator_id NOT NULL Rule 2 + reason
- DISPUTE 4,6,7,11 повреждена/потеряна/перепутана → investigation + PAYMENT_REFUNDED declared_value если потеряна + operator_id Rule 2 + фото обязательно Rule 4
