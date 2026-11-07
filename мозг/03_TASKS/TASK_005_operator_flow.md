# TASK_005 — Operator Flow — Dashboard фин operator_id + Price Lock v1 не удаляется
Дата: 2026-11-04
SSOT: TASK_001 DDL payments operator_id, TASK_003 Price Lock, TASK_004 payment API

## Поток оператора — Dashboard

### Список заказов — 8 статусов

| Статус | Что видит оператор | Кнопки | Rule |
|---|---|---|---|
| NEW | Заказ #123 QR-001 Платье | [Создать оценку v1] | Rule 7 QR только в items + Rule 3 snapshot |
| ESTIMATED | Оценка v1 1000 + фото 5 этапов | [Отправить клиенту Telegram] | Rule 3 v1 не удаляется + Rule 5 immutable |
| AGREED | Клиент согласен CUSTOMER_AGREED | [Захолдить платеж] disabled пока нет operator_id → требует operator_id NOT NULL Rule 2 | Rule 2 AI не допущен |
| IN_WORK | В работе, если доп дефект | [Создать v2] — v1 не удаляется, создается рядом Rule 3 + [Фото доп дефекта] | Rule 3 Price Lock |
| READY | Готово к выдаче | [Выдать курьеру] → сканировать QR | Rule 7 qr_code UNIQUE |
| OUT_FOR_DELIVERY | Курьер везет | Трекинг + [Исключения] | — |
| DELIVERED | Доставлено, фото возврата | [Списать] PAYMENT_CAPTURED disabled пока нет return_confirmations photo_url NOT NULL Rule 4 + operator_id Rule 2 | Rule 4 + Rule 2 |
| CLOSED | Закрыт, чек | Архив, просмотр истории v1,v2,v3 + events + transfer_history immutable | Rule 5 нельзя DELETE/UPDATE |

### Фин операции — только с operator_id Rule 2

#### 1. HOLD — AGREED→IN_WORK
Кнопка [Захолдить платеж]
- Требует: operator_id UUID NOT NULL — выбор оператора в dropdown
- Без operator_id — кнопка disabled + tooltip "Выберите оператора — Rule 2 AI не допущен"
- API: POST /api/payment/hold {order_id, amount, operator_id NOT NULL, idempotency_key UNIQUE}
- Пишет: payments + events PAYMENT_HOLD idempotency_key UNIQUE + transfer_history

#### 2. CAPTURE — DELIVERED→CLOSED
Кнопка [Списать]
- Требует: operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed
- Без фото возврата — disabled "Нет фото возврата — Rule 4"
- Без operator_id — disabled "Выберите оператора — Rule 2"
- API: POST /api/payment/capture {order_id, operator_id NOT NULL, return_confirmations_id, idempotency_key}
- Пишет: PAYMENT_CAPTURED + CLOSED

#### 3. REFUND — CANCELLED/DISPUTE
Кнопка [Возврат денег]
- Требует: operator_id NOT NULL Rule 2 + reason
- Для потеряна исключение 6 — возврат declared_value
- API: POST /api/payment/refund {order_id, operator_id NOT NULL, reason, idempotency_key}

### Price Lock — v1 не удаляется Rule 3

- В карточке заказа история:
  ```
  v1 1000 руб 2026-11-04 21:00 — отклонена? согласована? — остается
  v2 1200 руб 2026-11-04 22:00 — согласована — snapshot
  ```
- snapshot price_version_id — даже если прайс поменяется, у заказа старый
- В БД: price_versions immutable, estimates version INT, старая не удаляется
- В UI: кнопка [Создать v2] — создает новую рядом, не удаляет v1

### Immutable — Rule 5

- В Dashboard events + transfer_history только просмотр
- Нет кнопок [Удалить][Изменить]
- RULE DO INSTEAD NOTHING в БД — даже если хак

### QR — Rule 7

- В карточке вещи QR-001 показывается из items.qr_code UNIQUE
- Не из orders — вещь, не заказ
- При скане проверка UNIQUE

### Защита от дублей

- idempotency_key UNIQUE — оператор 2 раза жмет Списать — второй не вставится duplicate key
- Показывает "Уже обработано"
