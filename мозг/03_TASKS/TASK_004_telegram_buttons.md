# TASK_004 — Telegram Buttons — Согласен/Отказываюсь + idempotency_key
Дата: 2026-11-04
SSOT: TASK_003 Price Lock, TASK_002 State Machine

## Кнопки Telegram — как вшивает защиту от дублей

### Сообщение клиенту при ESTIMATED

```
🧵 Ателье Пермский ремонт
Вещь: Платье QR-001
Оценка: 1000 руб (v1)
Фото: [5 этапов по Rule 3]
Дефект: ...

[✅ Согласен v1] [❌ Отказываюсь]
```

callback_data формат:
- agree:{order_id}:{version} — Согласен
- reject:{order_id}:{version} — Отказываюсь

### Защита от дублей — idempotency_key UNIQUE

При каждом клике генерируется:
```
{order_id}:{event_type}:{ISO8601}:{random4}
Пример: 550e8400:CUSTOMER_AGREED:2026-11-04T21:30:00:ab12
```

- База: events.idempotency_key UNIQUE NOT NULL
- Если клиент 2 раза жмет Согласен — второй INSERT падает duplicate key
- Деньги не спишутся 2 раза
- Telegram показывает "Уже обработано"

### Поток v1 → v2

1. ESTIMATED v1 → Telegram [Согласен v1][Отказываюсь]
2. Если Отказываюсь → CUSTOMER_REJECTED → CANCELLED, вещь возвращается
3. Если Согласен v1 → CUSTOMER_AGREED → AGREED → PAYMENT_HOLD с operator_id (Rule 2)
4. IN_WORK → мастер нашел доп дефект → создается ESTIMATE_V2_CREATED, v1 не удаляется
5. Telegram снова: [Согласен v2][Отказываюсь v2] + фото доп дефекта
6. v1 остается в БД — аудит, Rule 3 нельзя менять цену без версии

### API Contract

POST /api/telegram/callback
Вход: {callback_data, idempotency_key UNIQUE, telegram_user_id, order_id}
Выход: {event, estimate_status, order_status}
Правило: проверка version актуальной — если v2 уже создана, v1 нельзя agree

### Связь с State Machine + Конституцией

- NEW→ESTIMATED: требует ESTIMATE_V1_CREATED + фото 5 этапов (Rule 3)
- ESTIMATED→AGREED: требует CUSTOMER_AGREED с idempotency_key UNIQUE
- Защита: UNIQUE не даст вставить дубль
- Rule 5: events immutable DO INSTEAD NOTHING
