# CONTEXT — текущий фокус
Дата: 2026-11-05 05:20 AM
Ветка: PLANNER

✅ Задание 000 — ЧИСТКА — DONE
✅ Задание 001 — ER-модель 20 сущностей — DONE (2026-11-05)

Что сделано в 001:
- Order 1:N Garment CASCADE индекс по order_id
- Garment 1:N EstimateVersion версионирование + partial unique is_current WHERE is_current
- Garment 1:N Photo типы reference/progress/fitting/defect/final
- Order 1:2 DeliveryLeg CHECK leg_number IN (1,2) + UNIQUE(order_id, leg_number) — 3-е плечо невозможно
- SQL схема v1 Postgres 15+ с 20 таблицами, ENUM статусами, pgcrypto UUID, seed measurements (6) и garment_types (6), триграм-индекс, GENERATED сумма
- KNOWLEDGE_GRAPH.md обновлен с mermaid ER-диаграммой и бизнес-правилами
- Файлы: KNOWLEDGE_GRAPH.md, schema_v1_draft.sql

Урок: защита CHECK + UNIQUE на leg_number — простое решение сложной бизнес-ошибки "создали 3-е плечо"

Следующее: Задание 002 — State Machine 8 шагов + 14 исключений курьера + миграции
Ветка: EXECUTOR_002 в новой вкладке

Очередь:
- 002: State Machine NEW→DELIVERED, Garment lifecycle, 14 исключений курьера таблица
- 003: Event Log + Price Lock
- 004: DDL финальный для b2.medium
- 005: docker-compose для гранта 10к
- 006: SOP QR
- 007: Concierge MVP без сервера

Правило: эта ветка только план, не выполняем код.
