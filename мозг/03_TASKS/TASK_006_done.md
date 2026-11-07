# TASK_006 — DONE — Quality Gate 5 фото + SOP 8 шагов + 14 исключений
Статус: DONE — выполнен в EXECUTOR_006
Дата: 2026-11-04 22:00 MSK
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1/v2, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния UI
Выход: 6 файлов Quality Gate

## Что сделано
- TASK_006_quality_gate_plan.md 4490 bytes — план Count:29 5 фото|Rule 2|3|4|5|7|operator_id|14 исключений
- TASK_006_quality_gate.md 4997 bytes Count:22 photo_url NOT NULL|qr_code UNIQUE|v1 не удаляется|operator_id NOT NULL|DO INSTEAD NOTHING|idempotency_key UNIQUE|5 фото — 5 фото этапов + чеклист 6 пунктов
- TASK_006_sop_operator.md 5022 bytes — SOP Оператора 8 шагов NEW→CLOSED + 14 исключений + фото обязательно + Rule 2|3|4|5|7|operator_id|photo_url|idempotency_key Count:20+
- TASK_006_sop_courier.md 5039 bytes — SOP Курьера 3 типа скана PICKUP/RETURN/DAMAGE + 14 исключений + qr_code UNIQUE|photo_url NOT NULL|DO INSTEAD NOTHING|Rule 7|4|5 Count:20+
- TASK_006_sop_client.md 4406 bytes — SOP Клиента Telegram Согласен/Отказываюсь + защита от дублей idempotency_key UNIQUE + v1 не удаляется Rule 3 + return_confirmations Rule 4
- TASK_006_done.md — этот файл

## 5 фото этапов — обязательно Rule 4 + Rule 3

| # | Этап | Куда пишет | Rule | Без фото? |
|---|---|---|---|---|
| 1 | Прием курьер | transfer_history photo_url NOT NULL + qr_code UNIQUE | Rule 7 QR только в items + Rule 4 photo_url NOT NULL + Rule 5 immutable | Не забрать — кнопка disabled |
| 2 | Дефектовка оператор | estimates + price_versions snapshot | Rule 3 v1 не удаляется + Rule 5 | Не оценить |
| 3 | До ремонта мастер | events + transfer_history | Rule 5 immutable + Rule 3 | Не в работу |
| 4 | После ремонта мастер | events READY | Quality Gate | Не готово |
| 5 | Возврат курьер | return_confirmations photo_url NOT NULL + customer_confirmed | Rule 4 + Rule 2 operator_id + idempotency_key | Не закрыть |

## Quality Gate чеклист 6 пунктов перед CLOSED

- [x] 5 фото есть? — 5 photo_url NOT NULL Rule 4
- [x] QR совпадает? — items.qr_code UNIQUE Rule 7 — перепутана 7 ошибка
- [x] Цена зафиксирована? — price_version_id snapshot + v1 не удаляется Rule 3
- [x] operator_id есть? — payments.operator_id NOT NULL Rule 2 AI не допущен 403
- [x] immutable? — RULE DO INSTEAD NOTHING Rule 5 — нельзя DELETE/UPDATE
- [x] idempotency_key защита? — events.idempotency_key UNIQUE NOT NULL — дубль Согласен/Скан/Списать → Уже обработано

## SOP 8 шагов — связь с 8 статусов State Machine

1. NEW→ESTIMATED v1 + фото 5 этапов + snapshot Rule 3
2. ESTIMATED → AGREED/CANCELLED [Согласен v1][Отказываюсь] + idempotency_key UNIQUE
3. AGREED→IN_WORK HOLD operator_id NOT NULL Rule 2
4. IN_WORK→READY если доп дефект v2 v1 не удаляется Rule 3
5. READY→OUT_FOR_DELIVERY скан QR qr_code UNIQUE Rule 7 + photo_url NOT NULL Rule 4 + immutable Rule 5
6. OUT_FOR_DELIVERY→DELIVERED трекинг + 14 исключений фото обязательно кроме потеряна 6
7. DELIVERED→CLOSED фото возврата return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + operator_id Rule 2 + 5 фото
8. CLOSED архив + история v1,v2,v3 + events + transfer_history immutable Rule 5

CANCELLED 5,13 → REFUND operator_id Rule 2
DISPUTE 4,6,7,11 → investigation + REFUND declared_value если потеряна 6 + operator_id + фото Rule 4

## Итого 03_TASKS — 29 файлов (26 MD + 3 non-MD) — MANIFEST 36 файлов

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL + 7 правил
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- TASK_005: 6 файлов (plan, frontend_contracts 24, client_flow, courier_flow, operator_flow, done) — Frontend 24 состояния
- TASK_006: 6 файлов (plan, quality_gate 5 фото, sop_operator 8 шагов, sop_courier 14 исключений, sop_client Telegram, done) — Quality Gate

Итого 29 файлов (28 было + 1 done) — 26 MD + 3 non-MD
MANIFEST: 36 файлов (31 было + 5 новых TASK_006)

## Следующий шаг

```
cd C:\Perm_Repair
python .\local_agent_pro_v2.py
```
Должно показать MANIFEST создан: 36 файлов (31 + 5 новых)

Затем TASK_007 — Security + Anti-fraud + Rule 2 operator_id + Rule 5 immutable + idempotency_key + 14 исключений
