# TASK_004 — QR Scan — transfer_history immutable + photo_url обязательно
Дата: 2026-11-04
SSOT: TASK_001 DDL transfer_history, TASK_002 14 исключений, TASK_003 events

## QR Scan — как вшивает 3 правила Конституции

### Rule 7: QR только в items

```sql
items(qr_code VARCHAR UNIQUE NOT NULL) -- только тут
orders — БЕЗ qr_code
transfer_history — БЕЗ qr_code, ссылка на item_id
```

При скане проверяется qr_code UNIQUE в items, не в orders

### Rule 5: immutable — нельзя DELETE/UPDATE

```sql
CREATE RULE no_update_transfer AS ON UPDATE TO transfer_history DO INSTEAD NOTHING;
CREATE RULE no_delete_transfer AS ON DELETE TO transfer_history DO INSTEAD NOTHING;
```

Нельзя подделать лог — даже если хак

### Rule 4: без фото не закрыть — photo_url NOT NULL

Скан без фото не вставит — обязательное поле

## 3 типа скана — API

### 1. PICKUP — забор у клиента / из пункта
POST /api/transfer/scan
{
  "order_id": "uuid",
  "item_qr_code": "QR-001-UNIQUE",
  "photo_url": "https://... NOT NULL",
  "operator_id": "uuid",
  "type": "PICKUP",
  "location": "клиент/пункт"
}
→ пишет transfer_history + events TRANSFER_SCANNED с idempotency_key UNIQUE

### 2. RETURN — возврат клиенту
{
  "order_id": "uuid",
  "item_qr_code": "QR-001",
  "photo_url": "https://... NOT NULL — Rule 4",
  "operator_id": "uuid",
  "type": "RETURN"
}
→ пишет return_confirmations photo_url NOT NULL + customer_confirmed → CLOSED
→ без photo_url не закрыть — Rule 4

### 3. DAMAGE — повреждение/потеря (14 исключений)
{
  "order_id": "uuid",
  "item_qr_code": "QR-001",
  "photo_url": "https://... фото повреждения обязательно",
  "type": "DAMAGE",
  "exception_id": "6 потеряна / 4 повреждена"
}
→ пишет events DISPUTE + order DISPUTE + investigation
→ исключение 6 потеряна → PAYMENT_REFUNDED с operator_id (Rule 2)

## Связь с 14 исключениями курьера (TASK_002)

| Исключение | Скан тип | Что пишет |
|---|---|---|
| 1 клиент не дома | RETURN fail | transfer_history + фото двери + exception 1 |
| 4 повреждена при заборе | PICKUP DAMAGE | photo_url повреждения + DISPUTE |
| 6 потеряна | DAMAGE | DISPUTE + PAYMENT_REFUNDED operator_id Rule 2 |
| 7 перепутана | PICKUP | проверка qr_code UNIQUE Rule 7 |
| 9 дверь не открыли | RETURN fail | фото + exception 9 |

## Все сканы пишут в 2 места

1. transfer_history immutable — аудит движения вещи
2. events с idempotency_key UNIQUE — защита от дублей скана

Если курьер 2 раза сканирует — второй не вставится из-за UNIQUE
