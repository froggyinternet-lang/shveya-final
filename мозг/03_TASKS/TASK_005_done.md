# TASK_005 — DONE — Frontend Contracts 3 фронта × 8 статусов + Конституция
Статус: DONE — выполнен в EXECUTOR_005
Дата: 2026-11-04
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1/v2, TASK_004 API 10 эндпоинтов
Выход: 6 файлов Frontend

## Что сделано
- TASK_005_frontend_contracts_plan.md — план Count:17 (operator_id|qr_code UNIQUE|photo_url NOT NULL|Согласен|v1 не удаляется)
- TASK_005_frontend_contracts.md — таблица 24 состояния UI + 2 исключения, Count:21 (Rule 2|Rule 3|Rule 4|Rule 5|Rule 7|idempotency_key|operator_id|qr_code UNIQUE|photo_url NOT NULL)
- TASK_005_client_flow.md — Telegram NEW→CLOSED + Согласен/Отказываюсь + idempotency_key защита, Count:16
- TASK_005_courier_flow.md — QR скан + 14 исключений + photo_url обязательно, Count:20 (qr_code UNIQUE|photo_url NOT NULL|DO INSTEAD NOTHING|Rule 7|Rule 4|Rule 5|потеряна)
- TASK_005_operator_flow.md — Dashboard фин operator_id + Price Lock v1 не удаляется, Count:20 (operator_id NOT NULL|Rule 2|Rule 3|Rule 4|Rule 5|v1 не удаляется|return_confirmations|idempotency_key)
- TASK_005_done.md — этот файл

## Как вшивает Конституцию в 3 фронта

### Rule 2: AI не допущен — operator_id обязателен
- Клиент: не видит operator_id, но платеж без него не пройдет
- Курьер: нет фин кнопок — только оператор
- Оператор: кнопка [Захолдить][Списать][Возврат] disabled пока нет operator_id NOT NULL — "Выберите оператора — Rule 2 AI не допущен" + 403 Forbidden без него
- БД: payments.operator_id UUID NOT NULL

### Rule 3: нельзя менять цену без версии — v1 не удаляется
- Клиент: видит историю v1 1000 → v2 1200, v1 остается аудит
- Оператор: карточка показывает v1,v2,v3 + snapshot price_version_id — даже если прайс поменяется, у заказа старый
- БД: price_versions immutable, estimates version INT, старая не удаляется

### Rule 4: без return_confirmations не закрыть
- Клиент: кнопка [Подтвердить возврат] → CLOSED требует return_confirmations photo_url NOT NULL + customer_confirmed
- Курьер: кнопка [Подтвердить] disabled пока нет photo_url NOT NULL — без фото не закрыть
- Оператор: кнопка [Списать] disabled пока нет return_confirmations photo_url NOT NULL Rule 4 + operator_id Rule 2
- БД: return_confirmations photo_url TEXT NOT NULL

### Rule 5: нельзя DELETE/UPDATE — immutable
- Клиент: не может удалить историю
- Курьер: transfer_history immutable RULE DO INSTEAD NOTHING — нельзя подделать лог
- Оператор: events + transfer_history только просмотр, нет кнопок удалить/изменить
- БД: 2 RULE DO INSTEAD NOTHING

### Rule 7: QR только в items
- Клиент: QR-001 показывается из items.qr_code UNIQUE
- Курьер: скан проверяет UNIQUE в items, не в orders — вещь, не заказ, при перепутана ошибка "QR не совпадает"
- Оператор: карточка вещи QR из items.qr_code UNIQUE
- БД: items(qr_code UNIQUE NOT NULL) — только тут, orders без qr_code

### Защита от дублей idempotency_key UNIQUE
- Telegram: клиент 2 раза жмет Согласен → второй INSERT падает duplicate key UNIQUE, показывает "Уже обработано", деньги не списываются 2 раза
- QR: курьер 2 раза сканирует → второй не вставится из-за UNIQUE
- Payment: оператор 2 раза жмет Списать → idempotency_key защита
- БД: events.idempotency_key UNIQUE NOT NULL

## Связь с 8 шагов + 14 исключений + 10 API + 13 таблиц

- State Machine 8 шагов: NEW→ESTIMATED→AGREED→IN_WORK→READY→OUT_FOR_DELIVERY→DELIVERED→CLOSED
- 14 исключений курьера: 1 клиент не дома фото двери, 4 повреждена фото повреждения, 6 потеряна DISPUTE + PAYMENT_REFUNDED operator_id, 7 перепутана qr_code UNIQUE проверка
- 10 API: telegram callback agree/reject idempotency_key, transfer scan PICKUP/RETURN/DAMAGE photo_url NOT NULL, payment hold/capture/refund operator_id NOT NULL, order create/estimate qr_code UNIQUE + price_version_id snapshot
- 13 таблиц DDL: orders, items qr_code UNIQUE, price_versions immutable, estimates version, events idempotency_key UNIQUE + immutable, transfer_history immutable + photo_url, payments operator_id NOT NULL, return_confirmations photo_url NOT NULL

## Критерий готовности — выполнен
- [x] 3 фронта описаны, каждый вшивает 5 правил Конституции
- [x] Клиент: кнопки Согласен/Отказываюсь + idempotency_key защита от дублей
- [x] Курьер: QR скан + qr_code UNIQUE Rule 7 + photo_url NOT NULL Rule 4 + 14 исключений
- [x] Оператор: operator_id обязателен Rule 2 + immutable Rule 5 + v1 не удаляется Rule 3
- [x] 24 состояния UI + 2 исключения CANCELLED/DISPUTE = 26 total

## Итого 03_TASKS — 23 файла (20 MD + 3 non-MD)

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL + 7 правил
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- TASK_005: 6 файлов (plan, frontend_contracts 24, client_flow, courier_flow, operator_flow, done) — Frontend Contracts
- Итого 23 файла (17 было + 6 новых)

## Следующий шаг
Запусти финальный манифест:
```
cd C:\Perm_Repair
python .\local_agent_pro_v2.py
```
Должно показать MANIFEST создан: 31 файл (25 было + 6 новых)

Затем TASK_006 — Quality Gate + 5 фото этапов + SOP — будет использовать все 5 TASK
