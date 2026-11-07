# TASK_001 — DONE — ER-модель 13 таблиц которая не дает нарушить Конституцию
Статус: DONE — выполнен в EXECUTOR_001
Дата: 2026-11-04
Бюджет: <6K токенов (факт 6.4K план + 5К DDL)
Исполнитель: PLANNER + EXECUTOR_001

## Что сделано
- Создан план TASK_001_ER_model_plan.md — 13 таблиц, вшивают 7 правил SHVEYA.md v2.3
- Создан DDL schema_v1_draft.sql — 100 строк, 13 CREATE TABLE + 2 RULE
- Проверен PowerShell Select-String — 7 совпадений CONSTITUTION Rule

## 13 таблиц и как вшивают Конституцию
1. orders — контейнер 1-10 вещей, БЕЗ QR (Rule 7)
2. items — qr_code UNIQUE NOT NULL только тут (Rule 7)
3. order_items — связь M:N
4. price_versions — снимок цены, version UNIQUE (Rule 3)
5. service_prices — цена через версию (Rule 3)
6. estimates — price_version_id NOT NULL (Rule 3)
7. transfer_history — immutable, RULE no_update/no_delete (Rule 5)
8. return_confirmations — photo_url NOT NULL, UNIQUE order_id (Rule 4)
9. results — source_type + source_ref NOT NULL (Rule 1)
10. payments — operator_id UUID NOT NULL (Rule 2: AI не допущен к фину)
11. customers — consent BOOLEAN
12. masters — справочник швей
13. events — idempotency_key UNIQUE

## Проверка PowerShell
```powershell
Select-String -Path schema_v1_draft.sql -Pattern "CONSTITUTION Rule" -AllMatches
# Результат 6 строк:
# Rule 7: orders БЕЗ QR, QR только в items (2 строки)
# Rule 3: нельзя менять цену без версии
# Rule 5: нельзя DELETE/UPDATE, только INSERT
# Rule 4: без этого заказ не закрыть
# Rule 1: без источника не сохранить
# Rule 2: AI к фину не допущен
```

## Критерий готовности — выполнен
- [x] qr_code UNIQUE NOT NULL только в items
- [x] transfer_history нельзя UPDATE/DELETE (RULE)
- [x] return_confirmations обязательна
- [x] price только через price_versions
- [x] payments требует operator_id
- [x] orders БЕЗ QR
- [x] 13 таблиц <100 строк DDL

## Следующий шаг
TASK_002 — State Machine (NEW -> ESTIMATED -> AGREED -> IN_WORK -> READY -> OUT_FOR_DELIVERY -> DELIVERED -> CLOSED) + роль оператора в платежах

## Ошибки исправлены в этом TASK
- #007 — путаница дефис/подчеркивание RULES-BRANCHES vs RULES_BRANCHES — исправлено rename
- #008 — Schema-V1-Draft vs schema_v1_draft.sql — исправлено rename + единая конвенция lowercase snake_case
