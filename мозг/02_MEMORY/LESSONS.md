# LESSONS — что узнали
Дата: 2026-11-05

1. Доставка 199+199 убивает ремонт 600р → решение Shveya Point + корзина 1-10
2. Context Rot после 50K токенов → Second Brain OS v2, бюджет <6.5K, ветки PLANNER vs EXECUTOR
3. Файловая система > Чат → все в мозг/
4. Зип не грузится на планшете → только по одному файлу container:///
5. TASK_001: CHECK leg_number IN (1,2) + UNIQUE(order_id, leg_number) — защита от 3-го плеча доставки простой DB констрейнтой, не кодом
6. TASK_001: partial unique index ux_estimate_current WHERE is_current — только одна актуальная смета на изделие
7. TASK_001: pgcrypto + seed measurements 6 + garment_types 6 — готовим словари сразу

## Улучшения для огромных проектов
- Одно задание = одна вкладка = не слабеет
- Оркестратор tab_orchestrator.py открывает вкладки как Claude Code
- KNOWLEDGE_GRAPH.md с mermaid + семантика ребер

8. TASK_002: State Machine 8 шагов + защита DB констрейнтами (state_transitions + CHECK + RULE DO INSTEAD NOTHING) — Конституция вшита в БД, не в код
9. TASK_002: 14 исключений курьера 6 колонок — покрывает оба плеча pickup/return, каждое пишет event source_type+source_ref
10. TASK_002: Garment 5 шагов + 3 кнопки швеи Приняла/Готово/Брак — каждая пишет transfer_history immutable + events idempotency_key UNIQUE
11. TASK_002: return_confirmations order_id UNIQUE + photo_url NOT NULL + customer_confirmed Rule 4 — без фото триггер блокирует закрытие
12. TASK_002: payments operator_id NOT NULL + yookassa_hold_id Rule 2+5 — AI не допущен к фин решениям

13. TASK_003-1: events idempotency_key формат {order_id}:{event_type}:{ts}:{rand6} + 3 UNIQUE индекса + RULE DO INSTEAD NOTHING — защита от дублей ЮKassa и двойного нажатия швеей — Rule 5
14. TASK_003-1: estimate_versions price_snapshot JSONB + is_current partial unique + RULE v1 не удаляется WHERE OLD.version_number=1 — Price Lock Rule 3 вшит в БД
15. TASK_003-1: transfer_history item_number проверка перепутана 7 из TASK_011 — ловит ошибку швеи на уровне БД
