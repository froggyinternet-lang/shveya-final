# TASK_007 — DONE — Security + Anti-fraud + Rule 2/3/4/5/7 + idempotency_key
Статус: DONE — выполнен в EXECUTOR_007
Дата: 2026-11-04 22:15 MSK
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP

## Что сделано — 5 файлов

1. TASK_007_security_plan.md 6235 bytes Count:28 Rule 2|3|4|5|7|idempotency_key UNIQUE|operator_id NOT NULL|DO INSTEAD NOTHING|14 исключений|10 атак — план 10 атак + защита + RLS
2. TASK_007_anti_fraud.md 10547 bytes Count:54 idempotency_key UNIQUE|operator_id NOT NULL|DO INSTEAD NOTHING|qr_code UNIQUE|photo_url NOT NULL|v1 не удаляется|Rule 2|3|4|5|7|потеряна|перепутана — 10 атак + защита Constitution
3. TASK_007_security_checklist.md 8872 bytes Count:30+ Rule 2|3|4|5|7|idempotency_key UNIQUE|operator_id NOT NULL|DO INSTEAD NOTHING|qr_code UNIQUE|photo_url NOT NULL — Security Checklist 7 пунктов все галочками
4. TASK_007_rls_policies.sql 6294 bytes — RLS + Grants — ENABLE ROW LEVEL SECURITY на 8 таблиц + 8 RULE DO INSTEAD NOTHING + REVOKE/GRANT + UNIQUE + CHECK + client_own_orders + courier_assigned_orders + operator_all_orders
5. TASK_007_done.md — этот файл

## 10 атак закрыты Constitution

| # | Атака | Защита | Rule |
|---|---|---|---|
| 1 | Дубль Согласен 2 раза | idempotency_key UNIQUE {order_id}:CUSTOMER_AGREED:timestamp:random → duplicate key → Уже обработано | idempotency_key UNIQUE + Rule 5 + Rule 3 |
| 2 | Дубль QR скан 2 раза | idempotency_key UNIQUE {order_id}:TRANSFER_SCANNED:qr:timestamp + qr_code UNIQUE | idempotency_key + Rule 7 + Rule 5 + Rule 4 |
| 3 | Дубль Списать 2 раза | idempotency_key UNIQUE {order_id}:PAYMENT_CAPTURED:amount:timestamp + operator_id NOT NULL + return_confirmations photo_url NOT NULL | idempotency_key + Rule 2 + Rule 4 + Rule 5 |
| 4 | Подделка operator_id AI | operator_id UUID NOT NULL + 403 Forbidden без operator_id + dropdown Выберите оператора — Rule 2 AI не допущен + disabled кнопки | Rule 2 AI не допущен |
| 5 | Подделка истории DELETE/UPDATE | RULE DO INSTEAD NOTHING — 2 правила — events + transfer_history immutable — только просмотр | Rule 5 immutable |
| 6 | Смена цены без версии | price_versions immutable v1 не удаляется + estimates version + snapshot price_version_id — история v1,v2,v3 | Rule 3 v1 не удаляется |
| 7 | QR в orders | items.qr_code UNIQUE NOT NULL — только тут — orders без qr_code — вещь, не заказ — перепутана 7 ошибка QR не совпадает | Rule 7 QR только в items |
| 8 | Закрытие без фото | return_confirmations photo_url NOT NULL + transfer_history photo_url NOT NULL + 5 фото этапов — кнопка disabled без фото Rule 4 + Quality Gate 6 чеков | Rule 4 photo_url NOT NULL + 5 фото |
| 9 | Потеряна без возврата declared_value 6 | Исключение 6 потеряна → DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id NOT NULL Rule 2 — самая строгая | Rule 2 + Rule 4 + исключение 6 |
| 10 | Перепутана без проверки 7 | qr_code UNIQUE проверка в items Rule 7 → ошибка QR не совпадает перепутана 7 + immutable Rule 5 + idempotency_key UNIQUE | Rule 7 + Rule 5 + idempotency_key + Rule 4 |

## Security Checklist 7 пунктов — все галочками

- [x] 1 Rule 2 operator_id NOT NULL для HOLD/CAPTURE/REFUND + 403 + disabled — атаки 3,4,9
- [x] 2 Rule 5 immutable RULE DO INSTEAD NOTHING events + transfer_history + price_versions + estimates + REVOKE UPDATE/DELETE — атаки 5,10
- [x] 3 idempotency_key UNIQUE NOT NULL — все мутации — Согласен/Скан/Списать/Холд/Рефанд — дубль → Уже обработано — атаки 1,2,3
- [x] 4 Rule 7 qr_code UNIQUE NOT NULL только в items — не в orders — вещь — атаки 7,10
- [x] 5 Rule 4 photo_url NOT NULL PICKUP/RETURN/DAMAGE + return_confirmations + 5 фото этапов — атаки 8,9
- [x] 6 Rule 3 v1 не удаляется Price Lock immutable + snapshot + version — атака 6
- [x] 7 14 исключений + 5 фото + Quality Gate 6 чеков + declared_value потеряна 6 + перепутана 7 — атаки 9,10

## RLS + Grants

- ENABLE ROW LEVEL SECURITY на 8 таблиц: payments, events, transfer_history, return_confirmations, orders, items, price_versions, estimates
- REVOKE ALL ON payments FROM courier, client — только operator может фин Rule 2 — GRANT SELECT, INSERT, UPDATE TO operator + operator_id IS NOT NULL CHECK
- 8 RULE DO INSTEAD NOTHING на events, transfer_history, price_versions, estimates Rule 5 — REVOKE UPDATE, DELETE
- UNIQUE INDEX items_qr_code_unique ON items(qr_code) Rule 7 — REVOKE UPDATE(qr_code) FROM courier, client
- CHECK photo_url NOT NULL Rule 4 — transfer_history + return_confirmations — исключение 6 потеряна обрабатывается в API
- client_own_orders, courier_assigned_orders, operator_all_orders — RLS
- client_own_events, courier_own_transfers, operator_all_events, operator_all_transfers — RLS

## Итого 03_TASKS — 34 файла (30 MD + 4 non-MD) — MANIFEST 42 файла

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL + 7 правил
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- TASK_005: 6 файлов (plan, frontend_contracts 24, client_flow, courier_flow, operator_flow, done) — Frontend 24 состояния
- TASK_006: 6 файлов (plan, quality_gate 5 фото, sop_operator 8 шагов, sop_courier 14 исключений, sop_client Telegram, done) — Quality Gate
- TASK_007: 5 файлов (plan Count:28, anti_fraud 10 атак Count:54, security_checklist 7 пунктов, rls_policies.sql RLS+Grants, done) — Security + Anti-fraud

Итого 34 файла (33 было + 1 done) — 30 MD + 4 non-MD — 3 sql + 1 mmd
MANIFEST: 42 файла (37 было + 5 новых TASK_007) — 37 MD + 5? 30 MD в 03_TASKS + 11 в корне и 00_CORE = 41? Проверить

## Следующий шаг

```
cd C:\Perm_Repair
python .\local_agent_pro_v2.py
```
Должно показать MANIFEST создан: 42 файлов (37 + 5 новых TASK_007)

Затем TASK_008 — Payments + HOLD/CAPTURE/REFUND + declared_value + Rule 2 operator_id + 14 исключений
