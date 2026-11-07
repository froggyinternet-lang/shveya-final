# MEMORY_INDEX — указатель где что лежит (30 сек чтения)
Дата: 2026-11-04
Ветка: PLANNER

## CORE — читай всегда (2K)
- SHVEYA.md v2.2 — операционка, правило веток, правило ошибок, 7 правил Конституции, ограничения (зип не грузится)
- RULES_BRANCHES.md — PLANNER vs EXECUTOR
- ERRORS.md — память ошибок #001-#003 + проверки
- BRAIN.md — весь мозг
- DECISIONS.md — почему b2.medium, Shveya Point приоритет

## PLANS — читай по нужде (по одному)
- PLAN_V5_MASTER_IMPLEMENTATION_SPEC.md — SSOT 69KB, 14 разделов (читать только раздел 5 для 001)
- PROGRESS_V5.md — чеклист 90 дней
- OPERATIONAL_PLAYBOOK_SOP_F0.10.md — 8 шагов оператора, 14 исключений курьера
- RISK_REGISTER_F0.11.md — 30+ рисков + Go/No-Go
- DATA_COLLECTION_PROTOCOL_F0.12.md — Garment не равно Order, QR, 5 этапов фото, сроки 30д/1г/5л

## MEMORY — обновляется каждый день
- KNOWLEDGE_GRAPH.md — 20 сущностей, будет 13 таблиц после 001
- LESSONS.md — доставка 199+199 убивает CM, Context Rot 50K, файловая система > чат
- CONTEXT.md — текущий фокус
- ERRORS.md — #001 зип, #002 слабее, #003 много файлов

## TASKS — одна задача = один файл <6K
- 00_TASK_LIST.md — 12 заданий по порядку
- TASK_001_ER_model_plan.md — 13 таблиц которые вшивают Конституцию (готов, ждет EXECUTOR_001)
- TASK_001_done.md — будет создан в EXECUTOR_001

## CODE
- C:\Perm_Repair через local_agent_pro_v2.py
- http://localhost:8000 — Сгенерить манифест

Правило: не грузи больше 3 файлов за раз!
Ограничение: зип не грузится на планшете — только container:// по одному файлу
