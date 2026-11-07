# KNOWLEDGE_GRAPH — будет заполнен в TASK_001

Order -> Garment (1:N) -> EstimateVersion -> Delivery (2 плеча) -> Payment

## Обновление 2026-11-05 — Rule 7

Item (было qr_code) → теперь:
- item_number VARCHAR(20) UNIQUE NOT NULL — PK для человека — PRM-2026-0001
- qr_code VARCHAR NULLABLE UNIQUE WHERE NOT NULL — опционально, = item_number когда будет принтер
- Связь: Item.item_number → TransferHistory.item_number — проверка при выдаче, ловит перепутана 7
- Photo 1 Приём: обязательно фото наклейки + вещи (наклейка 58x40 с item_number)

Order:
- order_number VARCHAR(20) UNIQUE NOT NULL — ORD-2026-0001 — для наклейки на пакете

Sequence:
- item_number_seq → generate_item_number()
- order_number_seq → generate_order_number()

## Обновление 2026-11-05 — TASK_002 State Machine + Courier Exceptions

State Machine Order 8 шагов:
NEW → ESTIMATING → CONFIRMED → PICKUP → IN_WORK → QC → READY → DELIVERED
+ CANCELLED из любого + DISPUTE из DELIVERED
Альтернатива: NEW → ESTIMATED → AGREED → IN_WORK → READY → OUT_FOR_DELIVERY → DELIVERED → CLOSED

Constraints:
- state_transitions(from_state, to_state, allowed_role) — 13 разрешенных, остальные запрещены триггером
- Нельзя NEW→IN_WORK, нельзя NEW→DELIVERED без ESTIMATING, нельзя назад из DELIVERED
- Каждый переход пишет immutable transfer_history + events idempotency_key UNIQUE

Garment lifecycle:
RECEIVED → INSPECTED → IN_WORK → QC → READY_FOR_RETURN + UNREPAIRABLE
3 кнопки: Приняла/Готово/Брак

Courier Exceptions 14:
1 клиент не отвечает 2 адрес неполный 3 отказ на месте 4 повреждение при доставке 5 опоздание >30м 6 перенос клиентом 7 пересорт QR_MISMATCH 8 дверь закрыта 9 отказ оплаты (54-ФЗ) 10 форс-мажор 11 потеря QR 12 pickup fail 13 дубль idempotency 14 конфликт
6 колонок: ответственный/уведомление/фин/срок/маршрут/рейтинг, пишет event source_type+source_ref

DeliveryLeg:
shoulder CHECK IN ('pickup','return') — 3-е плечо нельзя (защита из 001)
return_confirmations order_id UNIQUE + photo_url NOT NULL — Rule 4
