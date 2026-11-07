# TASK_004 — DONE — API Contracts 10 эндпоинтов + Telegram + QR + Payment
Статус: DONE — выполнен в EXECUTOR_004
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1/v2
Выход: 4 файла API

## Что сделано
- TASK_004_api_contracts_plan.md — план Count:21 (operator_id|idempotency_key|qr_code|return_confirmations|Согласен)
- TASK_004_api_contracts.md — таблица 10 эндпоинтов 6 колонок, Count:20 (/api/telegram|/api/transfer|/api/payment|operator_id|idempotency_key|qr_code UNIQUE)
- TASK_004_telegram_buttons.md — кнопки Согласен/Отказываюсь + защита от дублей idempotency_key UNIQUE, Count:13 (Согласен|idempotency_key|v1 не удаляется|CUSTOMER_AGREED)
- TASK_004_qr_scan.md — QR скан + immutable + photo_url NOT NULL, Count:10 (qr_code UNIQUE|DO INSTEAD NOTHING|photo_url NOT NULL|Rule 7|Rule 5|Rule 4)

## Как вшивает Конституцию (SHVEYA.md v2.3)

- Rule 2: AI не допущен к фину — POST /api/payment/hold|capture|refund требуют operator_id NOT NULL, без него 403 Forbidden
- Rule 3: нельзя менять цену без версии — POST /api/order/estimate snapshot price_version_id, v1 не удаляется создается v2 рядом, Price Lock
- Rule 4: без return_confirmations не закрыть — POST /api/payment/capture требует return_confirmations photo_url NOT NULL + customer_confirmed, без фото не CLOSED
- Rule 5: нельзя DELETE/UPDATE — все API пишут в events + transfer_history RULE DO INSTEAD NOTHING, нельзя подделать аудит
- Rule 7: QR только в items — POST /api/transfer/scan проверяет qr_code UNIQUE в items, не в orders, привязка к вещи

## Защита от дублей — idempotency_key

- Формат: {order_id}:{event_type}:{ISO8601}:{random4}
- Пример: 550e8400:CUSTOMER_AGREED:2026-11-04T21:30:00:ab12
- База: events.idempotency_key UNIQUE NOT NULL
- Telegram: клиент 2 раза жмет Согласен — второй INSERT падает duplicate key, деньги не списываются 2 раза, показывает "Уже обработано"
- QR: курьер 2 раза сканирует — второй не вставится из-за UNIQUE

## Связь с State Machine 002 + 14 исключениями

- NEW→ESTIMATED: /order/estimate → ESTIMATE_V1_CREATED
- ESTIMATED→AGREED: /telegram/callback agree → CUSTOMER_AGREED + idempotency_key
- AGREED→IN_WORK: /payment/hold + /transfer/scan PICKUP + operator_id
- OUT_FOR_DELIVERY→DELIVERED→CLOSED: /transfer/scan RETURN + /payment/capture требует return_confirmations photo_url Rule 4
- Исключения 1,4,6,7,9,11 → /transfer/scan DAMAGE с photo_url + DISPUTE/CANCELLED + PAYMENT_REFUNDED с operator_id Rule 2
- Исключения 5,13 → /telegram/callback reject → CUSTOMER_REJECTED → CANCELLED

## Критерий готовности — выполнен
- [x] 10 эндпоинтов описаны (3 telegram, 3 transfer, 3 payment, 1 order) с 6 колонками
- [x] Каждый фин требует operator_id NOT NULL Rule 2
- [x] Каждый пишет events idempotency_key UNIQUE + transfer_history immutable
- [x] Каждый проверяет qr_code UNIQUE Rule 7
- [x] Price Lock: snapshot price_version_id, v1 не удаляется
- [x] Telegram защита от дублей, QR photo_url обязательно

## Итого 03_TASKS — 17 файлов

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- Итого 17 файлов

## Следующий шаг
TASK_005 — Frontend Contracts (что показывать клиенту/курьеру/оператору) — будет использовать все 4 TASK DDL + API
