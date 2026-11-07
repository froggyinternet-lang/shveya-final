# CONTEXT — текущий фокус
Дата: 2026-11-05 05:30 AM
Ветка: PLANNER — TASK_002 DONE

✅ Задание 000 — ЧИСТКА — DONE
✅ Задание 001 — ER-модель 20 сущностей — DONE
  - Order 1:N Garment CASCADE
  - Garment 1:N EstimateVersion partial unique is_current
  - Order 1:2 DeliveryLeg CHECK IN (1,2) защита от 3-го плеча

✅ Задание 002 — State Machine 8 шагов + 14 исключений курьера + миграции — DONE (EXECUTOR_002)

Что сделано в 002:
- State Machine 8 шагов: NEW → ESTIMATING → CONFIRMED → PICKUP → IN_WORK → QC → READY → DELIVERED + CANCELLED из любого + DISPUTE из DELIVERED
  - Альтернативная ветка: NEW → ESTIMATED → AGREED → IN_WORK → READY → OUT_FOR_DELIVERY → DELIVERED → CLOSED
  - Защита: нет строки в state_transitions → триггер блокирует, нельзя NEW→IN_WORK, нельзя назад из DELIVERED
  - Вшивка Конституции:
    - NEW→ESTIMATED: Estimate v1 + 5 фото artifacts (Rule 3 Price Lock подготовка)
    - ESTIMATED→AGREED: customer_agreed + price_version_id Rule 3 Price Lock
    - AGREED→IN_WORK: payment_hold + operator_id NOT NULL + yookassa_hold_id Rule 2 + Rule 5 AI не допущен
    - DELIVERED→CLOSED: return_confirmations order_id UNIQUE + photo_url NOT NULL + customer_confirmed Rule 4 без фото DO INSTEAD NOTHING блокирует
- Garment 5 шагов: RECEIVED → INSPECTED → IN_WORK → QC → READY_FOR_RETURN + UNREPAIRABLE — 3 кнопки швеи Приняла/Готово/Брак, каждая пишет transfer_history immutable + events idempotency_key UNIQUE
- Таблица state_transitions: from_state, to_state, allowed_role (operator/master/courier) — 13 разрешенных
- 14 исключений курьера: клиент не дома, адрес не найден, вещь не готова, отказ от ремонта, повреждение при доставке, недовоз, перевес, оплата не прошла, клиент не отвечает, ПВЗ закрыт, возврат бракованный, потеря QR, двойная доставка, форс-мажор — 6 колонок: ответственный/уведомление/фин/срок/маршрут/рейтинг, покрывает 2 плеча pickup/return, каждое пишет event source_type+source_ref
- Миграции: migrations/001_initial.sql из schema_v1_draft.sql + вшивка Конституции 001
  - items.qr_code UNIQUE NOT NULL только в items, orders без QR, M:N через order_items
  - price_versions snapshot, service_prices UNIQUE, estimates → garment_id Price Lock, v1 не удаляется RULE DO INSTEAD NOTHING
  - transfer_history + events immutable, events idempotency_key UNIQUE + garment_id + source_type + source_ref
  - return_confirmations order_id UNIQUE + photo_url NOT NULL — без нее READY→DELIVERED невозможен
  - payments.operator_id NOT NULL + yookassa_hold_id + receipt 54-ФЗ — AI не допущен
  - deliveries shoulder CHECK IN ('pickup','return') — 3-е плечо нельзя, защита из 001 работает
  - Seed: measurements 6, garment_types 6, zones Мотовилиха, Shveya Points 2 точки
- Файлы: TASK_002_State_Machine.mmd, TASK_002_Courier_Exceptions.md, 001_initial.sql, TASK_002_done.md
- Бюджет <6.5K, читали только §3 SOP, zip не предлагал — Rule 2.3 соблюдено

Урок: State Machine + DB constraints (CHECK + UNIQUE + RULE DO INSTEAD NOTHING) — защита Конституции без кода

Следующее: Задание 003 — Event Log + Price Lock EstimateVersion v1/v2
Ветка: EXECUTOR_003 в новой вкладке

Очередь:
- 003: Event Log idempotency + Price Lock v1 не удаляется
- 004: DDL финальный для b2.medium
- 005: docker-compose для гранта 10к
- 006: SOP QR чеклисты
- 007: Concierge MVP без сервера

Правило: эта ветка только план.
