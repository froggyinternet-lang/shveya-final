# TASK_009 — Dashboard Operator — 16 колонок + 8 статусов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND
Дата: 2026-11-04
SSOT: SHVEYA.md v2.3 + TASK_008 Payments + TASK_007 Security + TASK_006 Quality Gate 5 фото + TASK_002 State Machine 8 шагов

## Dashboard Operator — таблица заказов

| Колонка | Что показывает | Rule | Откуда берется | Пример |
|---|---|---|---|---|
| order_id | ID заказа | — | orders.id | ORD-001 |
| status | 8 шагов NEW→ESTIMATED→AGREED→IN_WORK→READY→OUT_FOR_DELIVERY→DELIVERED→CLOSED + CANCELLED 5,13 + DISPUTE 4,6,7,11,12 | State Machine 8 шагов + 14 исключений | orders.status + TASK_002_state_machine | AGREED |
| client | Клиент Telegram | — | orders.client_id + Telegram @ | @nikita |
| courier | Курьер + трекинг + телефон | — | orders.courier_id + couriers.phone + transfer_history | Курьер Иван +7916123 + трекинг |
| operator_id | Оператор кто холдил/списал/вернул — обязательно Rule 2 | Rule 2 operator_id NOT NULL — AI не допущен — 403 без operator_id | payments.operator_id + events.operator_id | operator_123 — Выберите оператора Rule 2 если нет |
| items | Вещи в заказе | Rule 7 QR только в items — вещь, не заказ | items.name + items.qr_code UNIQUE | Платье красное + QR-001 |
| qr_code | QR код вещи UNIQUE — вещь | Rule 7 qr_code UNIQUE NOT NULL — только в items — не в orders — перепутана 7 ошибка QR не совпадает | items.qr_code UNIQUE | QR-001 — UNIQUE — если не совпадает → ошибка перепутана 7 |
| price_version | v1/v2/v3 + snapshot + история | Rule 3 v1 не удаляется — Price Lock — snapshot price_version_id — история v1,v2,v3 — v1 остается аудит | price_versions.version + estimates.price_version_id snapshot + history | v1 1000 руб snapshot + история v1 1000 → v2 1200 — v1 не удаляется Rule 3 |
| amount | HOLD/CAPTURE/REFUND amount или declared_value если потеряна 6 | Rule 2 + declared_value | payments.amount + orders.declared_value — для потеряна 6 declared_value, для остальных HOLD amount | HOLD 1000 руб / declared_value 5000 руб если потеряна 6 |
| declared_value | Объявленная стоимость вещи — для потеряна 6 — самая строгая | declared_value — для потеряна 6 возврат declared_value, не HOLD | orders.declared_value | 5000 руб — возврат полной стоимости если потеряна 6 — DISPUTE + investigation + operator_id Rule 2 |
| 5 фото | 5 фото этапов — Прием + Дефектовка + До ремонта + После ремонта + Возврат | Rule 4 photo_url NOT NULL + 5 фото — без фото не закрыть CLOSED + не выдать курьеру — Quality Gate 6 чеков | transfer_history.photo_url + return_confirmations.photo_url + estimates.photo_url — 5 фото — Прием + Дефектовка + До + После + Возврат | Фото 1 Прием QR-001 + Фото 2 Дефектовка + Фото 3 До + Фото 4 После + Фото 5 Возврат — если нет фото → Нет фото Rule 4 + disabled кнопка |
| Quality Gate | 6 чеков — 5 фото? QR совпадает? Цена зафиксирована? operator_id есть? immutable? idempotency_key? | Quality Gate 6 чеков + Rule 2/3/4/5/7 + idempotency_key UNIQUE | checklist: photo_url NOT NULL Rule 4 + qr_code UNIQUE Rule 7 + price_version_id snapshot Rule 3 + operator_id NOT NULL Rule 2 + RULE DO INSTEAD NOTHING Rule 5 + idempotency_key UNIQUE | [x] 5 фото [x] QR [x] Цена [x] operator_id [x] immutable [x] idempotency_key — все галочками — можно CLOSED |
| HOLD/CAPTURE/REFUND | Тип платежа + operator_id + idempotency_key + reason + exception_id 1-14 + declared_value если потеряна 6 | Rule 2 operator_id NOT NULL + idempotency_key UNIQUE + Rule 5 immutable + 14 исключений + declared_value | payments.type + operator_id + idempotency_key + reason + exception_id + declared_value + photo_url | HOLD operator_123 idempotency {order_id}:HOLD:1000:ts:rand UNIQUE — уже обработано если дубль / CAPTURE operator_123 photo_url NOT NULL Rule 4 + 5 фото + Quality Gate / REFUND operator_123 reason потеряна 6 declared_value 5000 Rule 2 + DISPUTE + investigation |
| exception | 14 исключений + фото + investigation + DISPUTE/CANCELLED | 14 исключений + Rule 4 photo_url NOT NULL кроме потеряна 6 + Rule 2 operator_id для DISPUTE + Rule 7 qr_code UNIQUE | transfer_history.exception_id + photo_url + events.exception_id + investigation | 1 клиент не дома retry + photo двери Rule 4 / 4 повреждена DISPUTE + photo повреждения Rule 4 + investigation + REFUND HOLD operator_id Rule 2 / 6 потеряна DISPUTE + investigation + REFUND declared_value 5000 самая строгая + operator_id Rule 2 / 7 перепутана QR не совпадает Rule 7 / 11 упаковка повреждена photo упаковки DISPUTE + REFUND |
| events | Лог всех событий immutable — нельзя DELETE/UPDATE — только просмотр — 12 типов + 3 платежа | Rule 5 immutable RULE DO INSTEAD NOTHING — нельзя DELETE/UPDATE — только INSERT + SELECT — лог не подделать — idempotency_key UNIQUE защита от дублей | events — только просмотр в Dashboard — RULE DO INSTEAD NOTHING — 12 типов + PAYMENT_HOLD/CAPTURED/REFUNDED + CUSTOMER_AGREED + TRANSFER_SCANNED + EXCEPTION + DISPUTE + CANCELLED | events log — immutable — нельзя удалить — только просмотр — idempotency_key UNIQUE — Уже обработано если дубль |
| transfer_history | Лог сканов QR + фото + exception + courier + operator + idempotency_key | Rule 7 qr_code UNIQUE + Rule 4 photo_url NOT NULL + Rule 5 immutable + idempotency_key UNIQUE + 14 исключений | transfer_history — только просмотр — immutable — PICKUP/RETURN/DAMAGE + qr_code UNIQUE Rule 7 + photo_url NOT NULL Rule 4 + exception_id + idempotency_key UNIQUE | PICKUP QR-001 photo_url NOT NULL Rule 4 courier_id + idempotency UNIQUE / RETURN QR-001 photo_url NOT NULL Rule 4 + exception 1 фото двери / DAMAGE QR-001 photo_url повреждения DISPUTE + exception 4 |
| created_at | Дата создания заказа + событий | — | orders.created_at + events.created_at + payments.created_at | 2026-11-04 22:00 |

## Фильтры Dashboard

- По статусу: NEW, ESTIMATED, AGREED, IN_WORK, READY, OUT_FOR_DELIVERY, DELIVERED, CLOSED, CANCELLED 5,13, DISPUTE 4,6,11,12
- По курьеру: все + по каждому курьеру + трекинг
- По оператору operator_id Rule 2: все + по каждому оператору — сколько HOLD/CAPTURE/REFUND
- По исключению 14: 1 не дома, 4 повреждена DISPUTE, 6 потеряна declared_value DISPUTE самая строгая, 7 перепутана qr_code UNIQUE, 11 упаковка повреждена DISPUTE
- По declared_value: только потеряна 6 — сумма REFUND declared_value
- По qr_code UNIQUE Rule 7: все QR + ошибки перепутана 7
- По photo_url Rule 4: без фото — Нет фото Rule 4 — 5 фото
- По v1/v2/v3 Rule 3: история версий — v1 не удаляется — snapshot
- По idempotency_key: дубли — Уже обработано — защита от дублей
- По дате: сегодня, неделя, месяц

## Действия Operator в Dashboard

- [Захолдить] — требует operator_id NOT NULL Rule 2 + amount snapshot Rule 3 + idempotency_key UNIQUE — HOLD — AGREED
- [Списать] — требует operator_id NOT NULL Rule 2 + return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + 5 фото + Quality Gate 6 чеков + idempotency_key UNIQUE — CAPTURE — CLOSED
- [Возврат денег] — требует operator_id NOT NULL Rule 2 + reason + idempotency_key UNIQUE + для потеряна 6 declared_value — REFUND — CANCELLED/DISPUTE — самая строгая потеряна 6 — DISPUTE + investigation + REFUND declared_value
- [Исключение] — выбрать из 14 — все требуют photo_url NOT NULL Rule 4 кроме потеряна 6 — DISPUTE/CANCELLED если 4,5,6,11,13 — investigation если DISPUTE
- Просмотр events + transfer_history — только просмотр — immutable Rule 5 — RULE DO INSTEAD NOTHING — нельзя DELETE/UPDATE — лог не подделать

## Telegram Buttons + Dashboard связь

- Client Telegram [✅ Согласен v1] [❌ Отказываюсь] + защита от дублей idempotency_key UNIQUE — триггер HOLD operator_id Rule 2
- Courier Telegram [Подтвердить забор] [Подтвердить возврат] [Исключение 14] + photo_url NOT NULL Rule 4 + qr_code UNIQUE Rule 7 + idempotency_key UNIQUE
- Operator Dashboard — все видит — 16 колонок — 8 статусов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + operator_id + declared_value + Quality Gate

## Итого Dashboard 16 колонок = 10 атак закрыты + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND
