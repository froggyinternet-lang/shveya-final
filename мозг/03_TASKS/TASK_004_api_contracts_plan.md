# TASK_004 — API Contracts — Telegram кнопки + QR скан + operator_id
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_004
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL (13 таблиц), TASK_002 State Machine (8 шагов + 14 исключений), TASK_003 Event Log (idempotency_key UNIQUE, Price Lock v1/v2)
Выход: API Contracts + TASK_004_done.md

## Что делать в EXECUTOR_004

### Часть 1: API Contracts — 3 группы

1. **Telegram API** — кнопки Согласен/Отказываюсь
   - POST /api/telegram/callback {callback_data: agree:{order_id}:{version}, idempotency_key}
   - Проверка estimate version актуальной
   - Пишет events CUSTOMER_AGREED/CUSTOMER_REJECTED с idempotency_key UNIQUE
   - Защита от дублей — второй клик не вставится

2. **QR Scan API** — transfer_history immutable
   - POST /api/transfer/scan {order_id, item_qr_code, photo_url NOT NULL, operator_id}
   - Проверка qr_code UNIQUE в items (Rule 7)
   - Пишет transfer_history + events TRANSFER_SCANNED
   - Фото обязательно — Rule 4 + Rule 5 immutable

3. **Payment API** — operator_id обязателен
   - POST /api/payment/hold {order_id, amount, operator_id NOT NULL} → AGREED→IN_WORK
   - POST /api/payment/capture {order_id, operator_id} → DELIVERED→CLOSED требует return_confirmations photo_url
   - POST /api/payment/refund {order_id, operator_id} → CANCELLED/DISPUTE
   - Rule 2: AI не допущен — без operator_id не провести фин операцию

### Часть 2: Как вшивает Конституцию

- Rule 2: все фин API требуют operator_id UUID NOT NULL
- Rule 3: price_version_id snapshot — даже если прайс поменяется, у заказа старый
- Rule 4: capture требует return_confirmations photo_url NOT NULL + customer_confirmed
- Rule 5: все API пишут в events + transfer_history immutable RULE DO INSTEAD NOTHING
- Rule 7: QR только в items — скан проверяет qr_code UNIQUE в items

### Часть 3: Связь с 14 исключениями курьера

- API скан с фото повреждения → исключение 4,6,7 → CANCELLED/DISPUTE
- API callback reject → исключение 5,13 → CANCELLED без ремонта
- API payment refund → исключение 6 потеряна → DISPUTE + возврат денег с operator_id

## Что создать в EXECUTOR_004

1. TASK_004_API_Contracts.md — таблица 10 эндпоинтов с 6 колонками (метод/путь/вход/выход/Rule/исключение)
2. TASK_004_Telegram_Buttons.md — кнопки Согласен/Отказываюсь + idempotency_key + защита от дублей
3. TASK_004_QR_Scan.md — скан QR + transfer_history immutable + photo_url обязательно
4. TASK_004_done.md — summary как API вшивают Конституцию

## Критерий готовности

- 10 эндпоинтов описаны (3 telegram, 3 transfer, 3 payment, 1 order)
- Каждый требует operator_id где фин (Rule 2)
- Каждый пишет в events idempotency_key UNIQUE + transfer_history immutable
- Каждый проверяет qr_code UNIQUE в items (Rule 7)
- Price Lock: snapshot price_version_id, v1 не удаляется

## Ограничения

- Один файл за раз через container:///, зип не предлагать
- Бюджет <6K, читать только TASK_001 DDL раздел API + TASK_002 State Machine раздел переходов + TASK_003 Event Log раздел idempotency_key
- Не выполнять 005 пока 004 не DONE
