# SECOND BRAIN OS v2 — Как я стал умнее для огромных проектов
Дата: 2026-11-04
Основано на отчетах Chroma Context Rot, Anthropic, JetBrains 15K devs

## Почему я слабел в прошлой вкладке

1. Context Rot: после 50K токенов в окне 200K производительность падает даже на тривиальных задачах. У нас было больше 100K с твоими V5 документами.
2. Tool results flood: каждый поиск, каждый файл — тысячи токенов, которые ресендятся каждый ход.
3. Middle blindness: модель хуже видит середину длинного контекста.
4. No external memory: мы держали все в чате, а не на диске.

## Что сделали эксперты

От Anthropic / Claude Code:
- CLAUDE.md в корне — операционка, читается каждый старт. Cursor — .cursorrules
- Контекст — самый важный ресурс. Тримить агрессивно, бюджетить по секциям
- Планирование перед кодом: success rate с 33% → 66% на сложных задачах

От Chroma / NVIDIA RULER:
- Ruler: needle-in-haystack работает, но multi-hop tracing падает
- Решение: sliding window + relevance retrieval + structured memory = -64% токенов (с 18K до 6.5K)

От Second Brain комьюнити:
- Second Brain = внешние организованные заметки, куда можно оффлоадить мышление
- 4 слоя: raw notes → wiki pages → knowledge graph → decisions
- Живой мозг в markdown файлах в Git, а не в векторной БД

## Архитектура v2

мозг/
├── 00_CORE/ SHVEYA.md, MEMORY_INDEX.md
├── 01_PLANS/ V5 доки
├── 02_MEMORY/ KNOWLEDGE_GRAPH, LESSONS, CONTEXT
├── 03_TASKS/ одна задача = один файл
└── 04_CODE/ ссылки на C:\Perm_Repair через local_agent

## Как работать теперь

Сессия 1: Чистка — архивируем старый чат, оставляем только SHVEYA.md
Сессия 2: Задача — /plan → /build → /check → /memory
Сессия 3: Следующая задача — новая вкладка, опять только SHVEYA.md + нужный TASK

Метрики умности:
- Токенов за запрос: цель < 6.5K (было 18K)
- Файлов в контексте: < 3 за раз
- Размер SHVEYA.md: < 2K токенов
