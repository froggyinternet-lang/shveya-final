# TASK_005 — Frontend Contracts — 3 фронта × 8 статусов = 24 состояния UI
Дата: 2026-11-04
SSOT: TASK_002 State Machine 8 шагов, TASK_004 API 10 эндпоинтов, TASK_003 Price Lock

## Таблица 24 состояния UI — 6 колонок

| # | Статус | Клиент Telegram | Курьер App | Оператор Dashboard | Rule | API |
|---|---|---|---|---|---|---|
| 1 | NEW | "Заказ создан QR-001" + кнопка [Отменить] | Не видит — еще не в работе | Список NEW, кнопка [Создать оценку v1] + price_version_id snapshot | Rule 7 QR только в items + Rule 3 snapshot | POST /api/order/create qr_code UNIQUE |
| 2 | ESTIMATED | Фото 5 этапов + цена 1000 v1 + [✅ Согласен v1] [❌ Отказываюсь] + idempotency_key защита | Не видит | Просмотр estimate v1 + фото, кнопка [Отправить клиенту] | Rule 3 v1 не удаляется + Rule 5 immutable events | POST /api/order/estimate v1 + telegram callback |
| 3 | AGREED | "Оплачено 1000, в работе" + idempotency_key UNIQUE защита от дублей | Видит PICKUP задача, кнопка [Сканировать QR забора] + photo_url NOT NULL обязательно | Кнопка [Захолдить платеж] требует operator_id NOT NULL Rule 2 + пишет PAYMENT_HOLD | Rule 2 operator_id + Rule 3 snapshot | POST /api/payment/hold operator_id + telegram agree |
| 4 | IN_WORK | "В работе у мастера" + прогресс | Мастер готов, кнопка [Готово к выдаче] + фото готово | Если доп дефект → кнопка [Создать v2] — v1 не удаляется Rule 3 + фото доп дефекта | Rule 3 v1 не удаляется создается v2 рядом + Rule 5 immutable | POST /api/order/estimate v2 ESTIMATE_V2_CREATED |
| 5 | READY | "Готово, ждите курьера" | Кнопка [Забрать из ателье] [Сканировать QR] + photo_url NOT NULL | Список READY к выдаче | Rule 7 qr_code UNIQUE проверка в items + Rule 5 transfer_history immutable | POST /api/transfer/scan PICKUP photo_url |
| 6 | OUT_FOR_DELIVERY | "Курьер везет" + трекинг | Список доставки, кнопка [Доставлено] [Сканировать QR возврата] + photo_url NOT NULL обязательно + кнопка [Исключение] + фото | Трекинг курьера | Rule 4 photo_url NOT NULL + Rule 5 immutable + Rule 7 QR | POST /api/transfer/scan RETURN photo_url NOT NULL |
| 7 | DELIVERED | Фото возврата + кнопка [Подтвердить возврат] → CLOSED требует return_confirmations photo_url NOT NULL Rule 4 + кнопка [Спор] | Кнопка [Фото возврата] — обязательно photo_url + customer_confirmed | Кнопка [Списать] PAYMENT_CAPTURED требует operator_id NOT NULL Rule 2 + return_confirmations photo_url Rule 4 | Rule 2 operator_id + Rule 4 photo_url + Rule 5 | POST /api/payment/capture operator_id + return_confirmations |
| 8 | CLOSED | "Заказ закрыт" + чек + return_confirmations фото | Не видит — закрыт | Архив, просмотр истории v1,v2,v3 + events + transfer_history immutable нельзя DELETE/UPDATE | Rule 5 нельзя DELETE/UPDATE + Rule 3 история версий | — |

## CANCELLED / DISPUTE — отдельные потоки

| Статус | Клиент | Курьер | Оператор | Rule | Исключение |
|---|---|---|---|---|---|
| CANCELLED | "Отменен" + причина + возврат денег если был HOLD | Возврат вещи в ателье [Сканировать QR возврата] | Кнопка [Возврат денег] PAYMENT_REFUNDED требует operator_id NOT NULL Rule 2 | Rule 2 operator_id | 5,13 клиент отказался |
| DISPUTE | "Спор, investigation" + фото повреждения | Кнопка [Фото повреждения] обязательно + exception_id 4,6,7,11 | Кнопка [Расследование] + [Возврат declared_value] требует operator_id Rule 2 | Rule 2 + Rule 4 photo_url + Rule 5 immutable | 4,6,7,11 повреждена/потеряна/перепутана |

## Детали UI — как вшивает Конституцию

### Rule 2: AI не допущен — operator_id обязателен
- В Dashboard кнопка фин операции [Захолдить][Списать][Возврат] disabled пока не выбран operator_id
- Без operator_id — 403 Forbidden
- В БД: payments.operator_id UUID NOT NULL

### Rule 3: v1 не удаляется — Price Lock
- В UI показывается история: v1 1000 (отклонена) → v2 1200 (согласована)
- Snapshot: даже если прайс поменяется, у заказа остается старый price_version_id
- В БД: price_versions immutable, estimates version INT

### Rule 4: без return_confirmations не закрыть
- Кнопка [Подтвердить возврат] → [Списать] неактивна пока нет return_confirmations photo_url NOT NULL + customer_confirmed
- Курьер не может закрыть без фото возврата

### Rule 5: immutable — нельзя DELETE/UPDATE
- В Dashboard events + transfer_history только просмотр, нет кнопок удалить/изменить
- RULE DO INSTEAD NOTHING в БД

### Rule 7: QR только в items
- Курьер сканирует QR-001 → проверка UNIQUE в items.qr_code
- Не в orders — вещь, не заказ
- При ошибке перепутана — скан покажет что QR не тот

### Защита от дублей idempotency_key
- Telegram: клиент 2 раза жмет Согласен → второй INSERT падает duplicate key UNIQUE, показывает "Уже обработано"
- QR: курьер 2 раза сканирует → второй не вставится из-за UNIQUE
- Payment: оператор 2 раза жмет Списать → idempotency_key защита

## 3 фронта × 8 статусов = 24 состояния UI + 2 исключения = 26 total

Все вшивает 5 правил Конституции + 10 API из TASK_004 + 8 шагов State Machine из TASK_002 + 13 таблиц DDL из TASK_001
