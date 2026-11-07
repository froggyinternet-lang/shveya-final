# TASK_002 — State Machine 8 шагов + 14 исключений курьера
Статус: PLAN — создан в PLANNER, будет выполнен в EXECUTOR_002
Дата: 2026-11-04
Бюджет: <6K токенов
Вход: SOP Ф0.10 (8 шагов оператора, швея 3 кнопки, курьер 14 исключений таблица), RISK Ф0.11, TASK_001 ERD
Выход: State Machine диаграмма mermaid + таблица 14 исключений + TASK_002_done.md

## Что делать в EXECUTOR_002 (маленькое задание)

### Часть 1: State Machine Order (8 статусов)

NEW → ESTIMATED → AGREED → IN_WORK → READY → OUT_FOR_DELIVERY → DELIVERED → CLOSED
Исключения: CANCELLED из любого, DISPUTE из DELIVERED

Переходы с условиями (вшивают Конституцию):
- NEW→ESTIMATED: нужен EstimateVersion v1 + фото 5 этапов
- ESTIMATED→AGREED: нужен customer_agreed=true + Price Lock (кнопки Согласен/Отказываюсь)
- AGREED→IN_WORK: нужен transfer_history (забор QR) + payment hold operator_id
- IN_WORK→READY: нужен master_done + QC чек-лист + фото готово
- READY→OUT_FOR_DELIVERY: нужен delivery_leg pickup RETURN подтвержден
- OUT_FOR_DELIVERY→DELIVERED: нужен delivery_leg return + фото возврата
- DELIVERED→CLOSED: нужен return_confirmations photo_url NOT NULL + customer_confirmed (Rule 4)

### Часть 2: State Machine Garment (5 статусов)

RECEIVED → INSPECTED → IN_WORK → QC → READY_FOR_RETURN

Каждый переход пишет в transfer_history (immutable) + events с idempotency_key

### Часть 3: 14 исключений курьера — таблица

Из SOP Ф0.10 — 14 исключений:
1. Клиент не дома
2. Адрес не найден
3. Вещь не готова
4. Вещь повреждена при заборе
5. Клиент отказался при заборе
6. Вещь потеряна
7. Вещь перепутана (чужой QR)
8. Курьер не приехал
9. Дверь не открыли
10. Фото не прошло Quality Gate
11. Упаковка повреждена
12. Заказ частично готов
13. Клиент просит вернуть без ремонта
14. Форс-мажор (ДТП, погода)

Для каждого: ответственный (Оператор/Курьер/Мастер), уведомление (кому), фин (кто платит), срок (SLA), маршрут (куда вещь), рейтинг (влияет или нет)

### Что создать в EXECUTOR_002

1. TASK_002_State_Machine.mmd — диаграмма mermaid stateDiagram-v2 8 статусов + 14 исключений
2. TASK_002_Courier_Exceptions.md — таблица 14 исключений с 6 колонками
3. TASK_002_done.md — summary как State Machine вшивает Конституцию (return_confirmations обязательна для CLOSED и тд)
4. Обновить KNOWLEDGE_GRAPH.md — добавить State Machine связи

## Критерий готовности

- Диаграмма 8 шагов + 2 доп CANCELLED/DISPUTE
- Переходы с условиями которые требуют файлы из TASK_001 (return_confirmations, transfer_history, price_versions)
- Таблица 14 исключений с 6 колонками (ответственный/уведомление/фин/срок/маршрут/рейтинг)
- Все переходы пишут в transfer_history immutable + events idempotency_key

## Ограничения

- Зип не грузится — один файл за раз через container:///
- Бюджет <6.5K, не грузить весь V5, только SOP Ф0.10 раздел 3 + RISK Ф0.11 раздел курьер
- Не выполнять 003 пока 002 не DONE

## Команда для старта EXECUTOR_002

"Начинаем TASK_002 — читаю SOP Ф0.10 8 шагов + 14 исключений"
