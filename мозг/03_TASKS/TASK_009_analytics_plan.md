# TASK_009 — Analytics + Dashboard + 5 фото отчет + operator_id + 14 исключений — PLAN
Дата: 2026-11-04 22:45 MSK
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_009
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP, TASK_007 Security 10 атак + RLS + Rule 2/3/4/5/7 + idempotency_key, TASK_008 Payments HOLD/CAPTURE/REFUND + declared_value + Rule 2

## Цель TASK_009

Вшить аналитику и дашборд оператора с защитой Constitution:

- Dashboard Operator: все заказы 8 статусов NEW→CLOSED + CANCELLED/DISPUTE + 14 исключений + 5 фото этапов + Quality Gate 6 чеков + HOLD/CAPTURE/REFUND + declared_value + operator_id Rule 2 + immutable Rule 5 + idempotency_key
- Analytics: сколько NEW, ESTIMATED, AGREED, IN_WORK, READY, OUT_FOR_DELIVERY, DELIVERED, CLOSED, CANCELLED, DISPUTE + по курьерам + по операторам operator_id + по исключениям 14 + по declared_value потеряна 6 + по qr_code UNIQUE Rule 7 + по photo_url Rule 4 + по v1/v2/v3 Rule 3
- 5 фото отчет: для каждого заказа 5 фото + чеклист 6 пунктов + Quality Gate — Прием + Дефектовка + До ремонта + После ремонта + Возврат — все photo_url NOT NULL Rule 4
- Rule 2: operator_id NOT NULL — все фин операции только оператор — 403 без operator_id — AI не допущен — дашборд показывает operator_id для HOLD/CAPTURE/REFUND
- Rule 5: immutable — events + transfer_history + payments + price_versions нельзя DELETE/UPDATE — RULE DO INSTEAD NOTHING — только просмотр в Dashboard — лог не подделать
- idempotency_key UNIQUE — защита от дублей — все мутации — Согласен/Скан/Списать/Холд/Рефанд — duplicate key → Уже обработано
- Rule 7: qr_code UNIQUE — вещь, не заказ — перепутана 7 ошибка QR не совпадает — дашборд показывает qr_code UNIQUE + история сканов
- Rule 4: photo_url NOT NULL + 5 фото — без фото не закрыть CLOSED + не выдать курьеру — дашборд показывает 5 фото + если нет фото — Нет фото Rule 4
- Rule 3: v1 не удаляется — Price Lock — история v1,v2,v3 + snapshot price_version_id — дашборд показывает историю версий
- 14 исключений: 1 клиент не дома retry + фото двери, 4 повреждена при заборе DISPUTE + фото повреждения + investigation + REFUND operator_id, 6 потеряна DISPUTE + investigation + REFUND declared_value самая строгая + operator_id Rule 2, 7 перепутана qr_code UNIQUE проверка, 11 упаковка повреждена фото упаковки DISPUTE

## Что делать в EXECUTOR_009 — 5 файлов

### 1. TASK_009_analytics_plan.md — этот файл — план

### 2. TASK_009_dashboard.md — Dashboard Operator — 8 статусов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND

Таблица дашборда:

| Колонка | Что показывает | Rule | Откуда |
|---|---|---|---|
| order_id | ID заказа | — | orders.id |
| status | 8 шагов NEW→CLOSED + CANCELLED 5,13 + DISPUTE 4,6,11,12 | State Machine 8 шагов + 14 исключений | orders.status |
| client | Клиент Telegram | — | orders.client_id |
| courier | Курьер + трекинг | — | orders.courier_id + transfer_history |
| operator_id | Оператор кто холдил/списал/вернул | Rule 2 operator_id NOT NULL | payments.operator_id + events.operator_id |
| items | Вещи + qr_code UNIQUE | Rule 7 QR только в items | items.qr_code UNIQUE + items.name |
| qr_code | QR код вещи | Rule 7 | items.qr_code UNIQUE |
| price_version | v1/v2/v3 + snapshot + история | Rule 3 v1 не удаляется | price_versions.version + estimates.price_version_id snapshot + history v1,v2,v3 |
| amount | HOLD/CAPTURE/REFUND amount или declared_value если потеряна 6 | Rule 2 + declared_value | payments.amount + orders.declared_value |
| declared_value | Объявленная стоимость для потеряна 6 | declared_value | orders.declared_value |
| 5 фото | Прием + Дефектовка + До + После + Возврат — 5 photo_url | Rule 4 photo_url NOT NULL + 5 фото | transfer_history.photo_url + return_confirmations.photo_url + estimates.photo_url — 5 фото |
| Quality Gate | 6 чеков: 5 фото? QR? Цена? operator_id? immutable? idempotency_key? | Quality Gate 6 чеков + Rule 2/3/4/5/7 | checklist |
| HOLD/CAPTURE/REFUND | Тип платежа + operator_id + idempotency_key + reason + exception_id | Rule 2 + idempotency_key UNIQUE + Rule 5 | payments.type + operator_id + idempotency_key + reason + exception_id |
| exception | 14 исключений + фото + investigation | 14 исключений + Rule 4 photo_url | transfer_history.exception_id + photo_url + events.exception_id |
| events | Лог всех событий immutable — нельзя DELETE/UPDATE | Rule 5 immutable + idempotency_key UNIQUE | events — только просмотр — RULE DO INSTEAD NOTHING |
| transfer_history | Лог сканов QR + фото + exception | Rule 7 + Rule 4 + Rule 5 + idempotency_key | transfer_history — только просмотр — immutable |
| created_at | Дата создания | — | orders.created_at + events.created_at |

### 3. TASK_009_analytics.sql — Analytics SQL — 8 статусов + 14 исключений + operator_id + declared_value

- Сколько NEW, ESTIMATED, AGREED, IN_WORK, READY, OUT_FOR_DELIVERY, DELIVERED, CLOSED, CANCELLED, DISPUTE
- По курьерам — сколько забрал/вернул/исключений 14
- По операторам operator_id — сколько HOLD/CAPTURE/REFUND — Rule 2
- По исключениям 14 — 1 не дома, 4 повреждена DISPUTE, 6 потеряна declared_value DISPUTE, 7 перепутана qr_code UNIQUE, 11 упаковка повреждена
- По declared_value — сколько потеряна 6 + сумма declared_value REFUND
- По qr_code UNIQUE — сколько сканов + ошибки перепутана 7 Rule 7
- По photo_url Rule 4 — сколько без фото — Нет фото Rule 4 — 5 фото
- По v1/v2/v3 Rule 3 — сколько v1, v2, v3 — история версий — v1 не удаляется
- По idempotency_key — сколько дублей отклонено — Уже обработано — защита от дублей

### 4. TASK_009_5_photo_report.md — 5 фото отчет + Quality Gate 6 чеков

| # | Этап | Фото куда | Rule | Без фото? | Что в отчете |
|---|---|---|---|---|---|
| 1 | Прием курьер | transfer_history photo_url NOT NULL + qr_code UNIQUE | Rule 7 + Rule 4 + Rule 5 immutable + idempotency_key UNIQUE | Не забрать — кнопка disabled + Нет фото забора Rule 4 | Фото вещи при заборе + QR + курьер + дата |
| 2 | Дефектовка оператор | estimates + price_versions snapshot photo_url | Rule 3 v1 не удаляется + Rule 5 + 5 фото | Не оценить | Фото дефектов + v1/v2/v3 + snapshot price_version_id |
| 3 | До ремонта мастер | events + transfer_history photo_url | Rule 5 immutable + Rule 3 + 5 фото | Не в работу | Фото до ремонта |
| 4 | После ремонта мастер | events READY photo_url | Quality Gate + 5 фото | Не готово — Quality Gate не пройден | Фото после ремонта + Quality Gate 6 чеков |
| 5 | Возврат курьер | return_confirmations photo_url NOT NULL + customer_confirmed | Rule 4 + Rule 2 operator_id + idempotency_key + 5 фото + Quality Gate | Не закрыть CLOSED — Нет фото возврата Rule 4 + Выберите оператора Rule 2 | Фото возврата + customer_confirmed + operator_id + CAPTURE |

Quality Gate 6 чеков в отчете: 5 фото? QR совпадает items.qr_code UNIQUE Rule 7? Цена зафиксирована price_version_id snapshot Rule 3? operator_id есть Rule 2? immutable Rule 5? idempotency_key UNIQUE защита от дублей?

### 5. TASK_009_done.md — summary

## Критерий готовности

- Dashboard таблица 16 колонок — 8 статусов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + operator_id + declared_value + qr_code UNIQUE + Quality Gate + events + transfer_history
- Analytics SQL — 9 запросов — по статусам 8 + CANCELLED/DISPUTE + по курьерам + по операторам operator_id Rule 2 + по исключениям 14 + по declared_value потеряна 6 + по qr_code Rule 7 + по photo_url Rule 4 + по v1/v2/v3 Rule 3 + по idempotency_key дублям
- 5 фото отчет — таблица 5 этапов + Quality Gate 6 чеков + Rule 2/3/4/5/7 + idempotency_key
- Все вшивает Constitution SHVEYA.md v2.3 + TASK_007 Security 10 атак + TASK_008 Payments HOLD/CAPTURE/REFUND

## Ограничения

- Один файл за раз через container:///
- Бюджет <6K
- Не выполнять 010 пока 009 не DONE
