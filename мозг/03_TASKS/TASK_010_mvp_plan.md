# TASK_010 — MVP Launch Checklist — Final Constitution + 7 правил + 8 шагов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + 10 атак — PLAN
Дата: 2026-11-04 23:15 MSK
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_010 — FINAL
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц + 7 правил, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется + 12 типов, TASK_004 API 10 эндпоинтов + Telegram Buttons + QR Scan, TASK_005 Frontend 24 состояния + client/courier/operator flows, TASK_006 Quality Gate 5 фото + 6 чеков + 3 SOP, TASK_007 Security 10 атак + RLS + Rule 2/3/4/5/7 + idempotency_key + qr_code UNIQUE + photo_url NOT NULL, TASK_008 Payments HOLD/CAPTURE/REFUND + declared_value + Rule 2 + 14 исключений, TASK_009 Analytics Dashboard 16 колонок + 9 запросов + 5 фото отчет + Quality Gate

## Цель TASK_010 FINAL

Финальный чеклист запуска MVP Perm_Repair с защитой Constitution SHVEYA.md v2.3 — все 7 правил + 8 шагов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + 10 атак + idempotency_key + RLS + Quality Gate — все галочками перед запуском

## Что делать в EXECUTOR_010 — 5 файлов

### 1. TASK_010_mvp_plan.md — этот файл — план

### 2. TASK_010_launch_checklist.md — MVP Launch Checklist — 50 пунктов — все галочками

### 3. TASK_010_constitution_final.md — Constitution Final — 7 правил + как вшиты во все слои

### 4. TASK_010_mvp_architecture.md — MVP Architecture — все 9 TASK + DDL + API + Frontend + SOP

### 5. TASK_010_done.md — summary FINAL — 10 TASK DONE — 57 файлов — MANIFEST 54-55

## Критерий готовности FINAL

- 50 пунктов Launch Checklist все галочками
- Constitution 7 правил вшиты: Rule 2 operator_id NOT NULL + 403 + dropdown, Rule 3 v1 не удаляется + snapshot + history, Rule 4 photo_url NOT NULL + 5 фото + disabled кнопки, Rule 5 immutable RULE DO INSTEAD NOTHING + REVOKE UPDATE/DELETE + только просмотр, Rule 7 qr_code UNIQUE NOT NULL только в items + перепутана 7 ошибка, idempotency_key UNIQUE защита от дублей Уже обработано + duplicate key, Rule? + 14 исключений + 5 фото + Quality Gate 6 чеков + HOLD/CAPTURE/REFUND + declared_value потеряна 6 самая строгая + 10 атак закрыты
- Architecture — все 9 TASK + DDL 13 таблиц + 7 правил + 8 шагов State Machine + 14 исключений + 12 типов Event Log + 10 эндпоинтов API + 24 состояния Frontend + 3 SOP + 5 фото Quality Gate + 10 атак Security + RLS + HOLD/CAPTURE/REFUND + declared_value + Analytics 16 колонок + 9 запросов + 5 фото отчет
- Все вшивает Constitution SHVEYA.md v2.3

## Ограничения

- Один файл за раз через container:///
- Бюджет <6K
- FINAL — после 010 — MVP Launch — можно запускать
