# TASK_007 — Security + Anti-fraud + Rule 2 + Rule 5 + idempotency_key — PLAN
Дата: 2026-11-04 22:15 MSK
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_007
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP

## Цель TASK_007

Вшить защиту от мошенничества и фрода во все слои:
- Rule 2: AI не допущен — operator_id NOT NULL для HOLD/CAPTURE/REFUND + 403
- Rule 5: immutable — RULE DO INSTEAD NOTHING — нельзя DELETE/UPDATE events + transfer_history
- idempotency_key UNIQUE — защита от дублей Согласен/Скан/Списать — duplicate key → Уже обработано
- Rule 7: QR только в items.qr_code UNIQUE — вещь, не заказ — перепутана 7 ошибка
- Rule 4: photo_url NOT NULL — без фото не закрыть CLOSED + не выдать курьеру
- Rule 3: v1 не удаляется — Price Lock snapshot

## Что делать в EXECUTOR_007 — 5 файлов

### 1. TASK_007_security_plan.md — этот файл — план

### 2. TASK_007_anti_fraud.md — Anti-fraud 10 атак + защита

| # | Атака | Что делает мошенник | Защита | Rule | API |
|---|---|---|---|---|---|
| 1 | Дубль Согласен | 2 раза жмет Согласен v1 чтобы списать 2 раза | idempotency_key UNIQUE {order_id}:CUSTOMER_AGREED:timestamp:random — второй INSERT падает duplicate key → Уже обработано | idempotency_key UNIQUE | POST /api/telegram/callback |
| 2 | Дубль QR скан | 2 раза сканирует QR-001 | idempotency_key UNIQUE {order_id}:TRANSFER_SCANNED:qr:timestamp — второй не вставится | idempotency_key + Rule 7 | POST /api/transfer/scan |
| 3 | Дубль Списать | Оператор 2 раза жмет Списать | idempotency_key UNIQUE {order_id}:PAYMENT_CAPTURED:amount:timestamp — второй падает | idempotency_key + Rule 2 | POST /api/payment/capture |
| 4 | Подделка operator_id | AI пытается списать без оператора | payments.operator_id UUID NOT NULL + 403 Forbidden без operator_id + dropdown "Выберите оператора — Rule 2 AI не допущен" | Rule 2 | HOLD/CAPTURE/REFUND |
| 5 | Подделка истории | Пытается DELETE/UPDATE events + transfer_history | RULE DO INSTEAD NOTHING — 2 правила — нельзя удалить — только просмотр в Dashboard | Rule 5 immutable | Все API |
| 6 | Смена цены без версии | Меняет цену v1 напрямую | price_versions immutable + v1 не удаляется + estimates version + snapshot price_version_id — старая остается аудит | Rule 3 | POST /api/order/estimate |
| 7 | QR в orders | Пытается положить QR в orders вместо items | items.qr_code UNIQUE NOT NULL — только тут — orders без qr_code — перепутана 7 ошибка "QR не совпадает" | Rule 7 | POST /api/order/create |
| 8 | Закрытие без фото | Пытается закрыть без photo_url | return_confirmations photo_url TEXT NOT NULL + transfer_history photo_url NOT NULL + 5 фото этапов — кнопка disabled без фото — Rule 4 | Rule 4 | POST /api/transfer/scan + capture |
| 9 | Потеряна без возврата | Теряет вещь и не возвращает declared_value | Исключение 6 потеряна → DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id NOT NULL Rule 2 + фото если есть | Rule 2 + 4 + 6 | REFUND |
| 10 | Перепутана без проверки | Отдает не ту вещь | qr_code UNIQUE проверка в items — скан проверяет UNIQUE — не совпадает → ошибка — нельзя выдать | Rule 7 | SCAN |

### 3. TASK_007_security_checklist.md — Security Checklist 7 пунктов

```
[ ] Rule 2: все фин API требуют operator_id NOT NULL — HOLD/CAPTURE/REFUND — без него 403
[ ] Rule 5: events + transfer_history immutable RULE DO INSTEAD NOTHING — нельзя DELETE/UPDATE
[ ] idempotency_key: все мутации требуют idempotency_key UNIQUE NOT NULL — Согласен/Скан/Списать/Холд/Рефанд — дубль → Уже обработано
[ ] Rule 7: qr_code только в items.qr_code UNIQUE NOT NULL — не в orders — вещь
[ ] Rule 4: photo_url NOT NULL для PICKUP/RETURN/DAMAGE + return_confirmations + 5 фото
[ ] Rule 3: price_versions immutable — v1 не удаляется — snapshot price_version_id — estimates version
[ ] 14 исключений: все требуют фото кроме потеряна 6 → DISPUTE + REFUND declared_value + operator_id
```

### 4. TASK_007_rls_policies.sql — RLS + Grants

- RLS policies для operator_id — только оператор видит фин кнопки
- Grants: courier не может HOLD/CAPTURE/REFUND — только оператор Rule 2
- client не может видеть events + transfer_history полностью — только свои
- immutable — REVOKE UPDATE/DELETE на events + transfer_history

### 5. TASK_007_done.md — summary

## Критерий готовности

- 10 атак описаны + защита Rule 2/3/4/5/7 + idempotency_key UNIQUE
- Security Checklist 7 пунктов
- RLS + Grants — courier не может фин, client не видит чужие
- Все вшивает Constitution SHVEYA.md v2.3

## Ограничения

- Один файл за раз через container:///
- Бюджет <6K
- Не выполнять 008 пока 007 не DONE
