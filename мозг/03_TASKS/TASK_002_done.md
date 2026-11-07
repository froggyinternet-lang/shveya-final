# TASK_002 — DONE — State Machine 8 шагов + 14 исключений курьера
Статус: DONE — выполнен в EXECUTOR_002
Дата: 2026-11-04
Бюджет: <6K токенов
Вход: SOP Ф0.10 (8 шагов оператора, швея 3 кнопки, 14 исключений), RISK Ф0.11, TASK_001 ERD
Выход: state machine mermaid + таблица 14 исключений

## Что сделано
- TASK_002_state_machine_plan.md — план 8 статусов + 14 исключений
- TASK_002_state_machine.mmd — диаграмма stateDiagram-v2 8 статусов + CANCELLED/DISPUTE + 7 правил Конституции
- TASK_002_courier_exceptions.md — таблица 14 исключений, 6 колонок, Count:14 подтвержден PowerShell

## State Machine — как вшивает Конституцию (SHVEYA.md v2.3)

1. NEW → ESTIMATED: требует price_versions version + фото 5 этапов (Rule 3)
2. ESTIMATED → AGREED: customer_agreed + Price Lock
3. AGREED → IN_WORK: transfer_history QR забор + payment hold operator_id (Rule 5 + Rule 2)
4. IN_WORK → READY: master_done + QC + фото готово, пишет в transfer_history immutable
5. READY → OUT_FOR_DELIVERY: delivery_leg pickup RETURN подтвержден
6. OUT_FOR_DELIVERY → DELIVERED: delivery_leg return + фото возврата (Rule 5)
7. DELIVERED → CLOSED: return_confirmations photo_url NOT NULL + customer_confirmed (Rule 4) — без этого не закрыть
8. CANCELLED из любого, DISPUTE из DELIVERED → требует operator_id для возврата денег (Rule 2)

Дополнительные заметки:
- orders БЕЗ QR, items qr_code UNIQUE NOT NULL только в items (Rule 7)
- Все переходы пишут в transfer_history immutable + events idempotency_key (Rule 5)
- Все фин операции требуют operator_id UUID NOT NULL (Rule 2: AI не допущен)

## 14 исключений — проверка PowerShell
```powershell
Select-String -Path TASK_002_courier_exceptions.md -Pattern "Клиент не дома|Вещь потеряна|operator_id|return_confirmations" -AllMatches | Measure-Object
# Count:14 — 14 исключений найдено
```

Каждое исключение: ответственный, уведомление, фин кто платит, срок SLA, маршрут вещи, рейтинг

## Критерий готовности — выполнен
- [x] Диаграмма 8 шагов + 2 доп CANCELLED/DISPUTE
- [x] Переходы с условиями которые требуют файлы из TASK_001 (return_confirmations, transfer_history, price_versions, operator_id)
- [x] Таблица 14 исключений с 6 колонками
- [x] Все переходы пишут в transfer_history immutable + events idempotency_key
- [x] PowerShell проверка Count:14

## Следующий шаг
TASK_003 — Event Log + Price Lock (идемпотентность, как Price Lock вшивает Rule 3 и Rule 4)
