# TASK_005 — Frontend Contracts — что показывать клиенту/курьеру/оператору
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_005
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key + Price Lock v1/v2, TASK_004 API 10 эндпоинтов
Выход: Frontend Contracts + TASK_005_done.md

## Что делать в EXECUTOR_005

### 3 фронта — 3 роли

1. **Клиент Telegram** — что видит клиент
   - NEW: "Заказ создан QR-001"
   - ESTIMATED: фото 5 этапов + цена 1000 + [Согласен][Отказываюсь] + idempotency_key защита
   - AGREED→IN_WORK: "Оплачено, в работе" + operator_id hold
   - READY→OUT_FOR_DELIVERY: "Готово, курьер везет"
   - DELIVERED: фото возврата + [Подтвердить возврат] → CLOSED требует return_confirmations photo_url Rule 4
   - DISPUTE: "Спор, investigation" + PAYMENT_REFUNDED с operator_id Rule 2

2. **Курьер App** — QR скан + фото обязательно
   - Список заказов OUT_FOR_DELIVERY + адрес
   - Кнопка [Сканировать QR] → POST /api/transfer/scan + photo_url NOT NULL обязательно
   - Проверка qr_code UNIQUE в items Rule 7
   - 14 исключений — кнопка [Исключение] + фото повреждения обязательно → DISPUTE
   - Нельзя закрыть без фото — Rule 4 + Rule 5 immutable

3. **Оператор Dashboard** — фин операции только с operator_id
   - Список заказов NEW→ESTIMATED — создать estimate v1 + price_version_id snapshot Rule 3
   - Кнопка [Захолдить платеж] → PAYMENT_HOLD требует operator_id NOT NULL Rule 2
   - Кнопка [Списать] → PAYMENT_CAPTURED требует return_confirmations photo_url Rule 4 + operator_id Rule 2
   - Кнопка [Возврат] → PAYMENT_REFUNDED требует operator_id Rule 2 + reason
   - Просмотр events + transfer_history immutable — нельзя DELETE/UPDATE Rule 5
   - v1 не удаляется — показать историю v1,v2,v3

### Как вшивает Конституцию в UI

- Rule 2: кнопка фин операции неактивна без выбора оператора — AI не допущен
- Rule 3: цена показывается с версией snapshot, даже если прайс поменяется — старая не меняется
- Rule 4: кнопка CLOSED неактивна пока нет return_confirmations photo_url + customer_confirmed
- Rule 5: в dashboard нельзя удалить/изменить events + transfer_history — только просмотр
- Rule 7: в курьерском приложении QR сканируется только из items.qr_code UNIQUE

## Что создать в EXECUTOR_005

1. TASK_005_frontend_contracts.md — таблица 3 фронта × 8 статусов = 24 состояния UI
2. TASK_005_client_flow.md — Telegram поток клиента NEW→CLOSED + кнопки Согласен/Отказываюсь + защита от дублей
3. TASK_005_courier_flow.md — QR скан + 14 исключений + photo_url обязательно
4. TASK_005_operator_flow.md — Dashboard фин операции operator_id + Price Lock v1 не удаляется
5. TASK_005_done.md — summary

## Критерий готовности

- 3 фронта описаны, каждый вшивает 5 правил Конституции
- Клиент: кнопки Согласен/Отказываюсь + idempotency_key защита
- Курьер: QR скан + qr_code UNIQUE Rule 7 + photo_url NOT NULL Rule 4
- Оператор: operator_id обязателен Rule 2 + immutable Rule 5
- Price Lock: v1 не удаляется, показывается история версий Rule 3

## Ограничения

- Один файл за раз через container:///, зип не предлагать
- Бюджет <6K, читать только TASK_004 API раздел 10 эндпоинтов + TASK_002 State Machine 8 шагов
- Не выполнять 006 пока 005 не DONE
