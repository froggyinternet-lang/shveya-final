# TASK_006 — Quality Gate + 5 фото этапов + SOP оператору
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_006
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key + Price Lock v1/v2, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния
Выход: Quality Gate + SOP + TASK_006_done.md

## Что делать в EXECUTOR_006

### 5 фото этапов — Quality Gate

Каждый заказ требует 5 фото по Rule 3 + Rule 4:

1. **Прием** — фото вещи при заборе (курьер) — transfer_history photo_url NOT NULL + qr_code UNIQUE Rule 7
2. **Дефектовка** — фото дефекта (мастер) — estimate v1 + price_version_id snapshot Rule 3
3. **До ремонта** — фото до ремонта — immutable events Rule 5
4. **После ремонта** — фото после ремонта — quality gate check
5. **Возврат** — фото возврата клиенту — return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed → CLOSED

Без 5 фото нельзя закрыть — Rule 4 + Rule 3

### Quality Gate — проверка

- [ ] 5 фото есть? — без фото не CLOSED Rule 4
- [ ] QR совпадает? — qr_code UNIQUE в items Rule 7
- [ ] Цена зафиксирована? — price_version_id snapshot Rule 3, v1 не удаляется
- [ ] operator_id есть для фина? — Rule 2 AI не допущен, без operator_id 403
- [ ] events + transfer_history immutable? — Rule 5 нельзя DELETE/UPDATE RULE DO INSTEAD NOTHING
- [ ] idempotency_key защита? — duplicate key UNIQUE не даст списать 2 раза

### SOP оператору — 8 шагов

1. NEW → создать оценку v1 + фото 5 этапов + price_version_id snapshot Rule 3
2. ESTIMATED → отправить клиенту Telegram [Согласен v1][Отказываюсь] + idempotency_key UNIQUE защита
3. AGREED → захолдить платеж с operator_id NOT NULL Rule 2 + PAYMENT_HOLD
4. IN_WORK → если доп дефект → создать v2, v1 не удаляется Rule 3 + фото доп дефекта
5. READY → выдать курьеру + скан QR + photo_url NOT NULL Rule 7+4 + transfer_history immutable Rule 5
6. OUT_FOR_DELIVERY → трекинг + 14 исключений курьера — фото обязательно кроме потеряна
7. DELIVERED → фото возврата + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed
8. CLOSED → списать с operator_id NOT NULL Rule 2 + PAYMENT_CAPTURED + idempotency_key защита

Исключения:
- CANCELLED → клиент отказался 5,13 → PAYMENT_REFUNDED operator_id Rule 2
- DISPUTE → повреждена 4, потеряна 6, перепутана 7, упаковка 11 → DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id Rule 2 + фото обязательно Rule 4

### Что создать в EXECUTOR_006

1. TASK_006_quality_gate.md — чеклист 5 фото + 5 правил Конституции + 10 API
2. TASK_006_sop_operator.md — SOP 8 шагов + 14 исключений + фото обязательно
3. TASK_006_sop_courier.md — SOP курьеру QR скан + photo_url + 14 исключений
4. TASK_006_sop_client.md — SOP клиенту Telegram Согласен/Отказываюсь + защита от дублей
5. TASK_006_done.md — summary 6 TASK = 28 файлов

## Критерий готовности

- 5 фото этапов описаны + Rule 3 + Rule 4
- Quality Gate чеклист 6 пунктов — 5 правил + idempotency_key
- SOP 8 шагов оператору + 14 исключений + фото обязательно
- Все вшивает Конституцию SHVEYA.md v2.3 + DDL + State Machine + Event Log + API + Frontend

## Ограничения

- Один файл за раз через container:///, зип не предлагать
- Бюджет <6K, читать только TASK_005 Frontend 24 состояния + TASK_002 14 исключений
- Не выполнять 007 пока 006 не DONE
