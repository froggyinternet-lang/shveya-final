# TASK_003 — Event Log + Price Lock (EstimateVersion v1/v2) + idempotency_key
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_003
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL (events idempotency_key UNIQUE, price_versions, estimates), TASK_002 State Machine (ESTIMATED→AGREED требует Price Lock), DATA Ф0.12 (EstimateVersion не удаляется)
Выход: Event Log таблица + Price Lock логика + TASK_003_done.md

## Что делать в EXECUTOR_003

### Часть 1: Event Log — как не потерять событие

Таблица из 001:
events(
  id UUID,
  order_id UUID,
  garment_id UUID, -- привязка к вещи, не к заказу
  idempotency_key VARCHAR(100) UNIQUE NOT NULL, -- защита от дублей
  event_type VARCHAR(50), -- ORDER_CREATED, ESTIMATE_V1_CREATED, CUSTOMER_AGREED, TRANSFER_SCANNED, PAYMENT_HOLD, RETURN_CONFIRMED
  payload JSONB,
  created_at TIMESTAMPTZ
)

Правила:
- Каждое действие пишет в events + transfer_history
- idempotency_key = order_id + event_type + timestamp + random (уникален)
- Если дубль прилетит — база не даст вставить (UNIQUE), защита от двойного списания
- events immutable — RULE DO INSTEAD NOTHING на UPDATE/DELETE как в transfer_history

### Часть 2: Price Lock — EstimateVersion v1/v2 не удаляется

Из V5 и DATA Ф0.12:
- EstimateVersion v1 создается при оценке: price, price_version_id снимок, photo_url
- Клиент видит в Telegram 2 кнопки: Согласен / Отказываюсь
- Если Согласен → status AGREED, пишем event CUSTOMER_AGREED, idempotency_key
- Если Отказываюсь → status REJECTED, вещь возвращается, event CUSTOMER_REJECTED
- Если мастер нашел доп дефект → создается EstimateVersion v2, старая v1 НЕ удаляется, новая v2 с новым price
- Клиент снова видит Согласен/Отказываюсь уже для v2
- В заказе хранится snapshot price_version_id — даже если прайс поменяется, у заказа старый

Таблица estimates:
id, item_id, price_version_id, version INT (1,2), price, status, photo_url, created_at

### Часть 3: Связь с State Machine

- NEW→ESTIMATED: создает event ESTIMATE_V1_CREATED с idempotency_key, пишет estimate v1
- ESTIMATED→AGREED: требует event CUSTOMER_AGREED с idempotency_key, проверяет estimate status AGREED
- AGREED→IN_WORK: требует event PAYMENT_HOLD с operator_id
- Любой дубль кнопки Согласен — второй раз не вставится из-за UNIQUE idempotency_key

### Что создать в EXECUTOR_003

1. TASK_003_Event_Log.sql — CREATE TABLE events + RULE immutable + COMMENT -- CONSTITUTION Rule
2. TASK_003_Price_Lock.md — логика v1/v2, кнопки Согласен/Отказываюсь, как v1 не удаляется, snapshot
3. TASK_003_Event_Types.md — список 10 типов событий с idempotency_key форматом
4. TASK_003_done.md — summary как Event Log + Price Lock вшивают Конституцию (защита от дублей, от изменения цены без версии)

## Критерий готовности

- events idempotency_key UNIQUE NOT NULL, immutable RULE
- estimates version INT, старая не удаляется, новая v2 создается рядом
- Price Lock: кнопки Согласен/Отказываюсь, без согласия не взять в работу (из State Machine 002)
- Каждый переход State Machine пишет в events + transfer_history
- Snapshot price_version_id в заказе

## Ограничения

- Один файл за раз через container:///, зип не предлагать
- Бюджет <6.5K, читать только TASK_001 DDL раздел events + TASK_002 State Machine раздел ESTIMATED→AGREED + DATA Ф0.12 раздел EstimateVersion
- Не выполнять 004 пока 003 не DONE
