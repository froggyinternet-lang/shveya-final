# Telegram Бот Без Кода — 3 кнопки Приняла/Готово/Брак → Google Sheet

## Цель
Швея без приложения нажимает 3 кнопки в Telegram. Бот пишет в Google Sheet. Защита от дублей через MessageID (idempotency).

## Шаг 1 — BotFather (2 мин)
1. Telegram → найди @BotFather
2. /newbot
3. Name: `SHVEYA Concierge`
4. Username: `shveya_concierge_2026_bot` (уникальный)
5. Сохрани токен: `8123456789:AAH...`
6. /setcommands → вставь:
```
accepted - ✅ Приняла
ready - ✅ Готово
defect - ⚠️ Брак
```

## Шаг 2 — Создай 3 группы / чата
- Чат Операторов: добавь бота + операторов
- Чат Швеи: добавь бота + швею Зарему
- Чат Курьеров: добавь бота + курьера

Получи chat_id: напиши в чат @userinfobot → он вернет ID.

## Шаг 3 — n8n Workflow без кода (Make.com аналогично)

### Вариант A — n8n.cloud (рекомендуется, бесплатно)

#### Импортируй этот JSON в n8n → Import Workflow:

```json
{
  "name": "SHVEYA Concierge 3 кнопки",
  "nodes": [
    {
      "name": "Telegram Trigger",
      "type": "n8n-nodes-base.telegramTrigger",
      "credentials": {"telegramApi": "shveya_bot_token"},
      "parameters": {
        "updates": ["message", "callback_query"]
      }
    },
    {
      "name": "Parse PRM",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "const text = $json.message?.text || $json.callback_query?.data || '';
const match = text.match(/PRM-\d{4}-\d{4}/);
return [{prm: match ? match[0] : null, message_id: $json.message?.message_id || $json.callback_query?.message?.message_id, chat_id: $json.message?.chat?.id, from: $json.message?.from?.username, raw: text}];"
      }
    },
    {
      "name": "Check Duplicate MessageID",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "lookup",
        "sheet": "Events",
        "filters": {"message_id": "={{ $json.message_id }}"}
      }
    },
    {
      "name": "IF Duplicate?",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {"number": [{"value1": "={{ $json.length }}", "operation": ">", "value2": 0}]}
      }
    },
    {
      "name": "STOP Duplicate",
      "type": "n8n-nodes-base.stopAndError",
      "parameters": {"errorMessage": "Duplicate message_id — idempotency защита"}
    },
    {
      "name": "Route by Button",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "value1": "={{ $json.raw }}",
        "rules": [
          {"value": "Приняла", "operation": "contains"},
          {"value": "Готово", "operation": "contains"},
          {"value": "Брак", "operation": "contains"}
        ]
      }
    },
    {
      "name": "Update Orders ACCEPTED",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "update",
        "sheet": "Orders",
        "key": "item_number",
        "keyValue": "={{ $json.prm }}",
        "mapping": {"status": "ACCEPTED", "telegram_message_id": "={{ $json.message_id }}"}
      }
    },
    {
      "name": "Update Orders READY",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "update",
        "sheet": "Orders",
        "key": "item_number",
        "keyValue": "={{ $json.prm }}",
        "mapping": {"status": "READY"}
      }
    },
    {
      "name": "Update Orders DEFECT",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "update",
        "sheet": "Orders",
        "key": "item_number",
        "keyValue": "={{ $json.prm }}",
        "mapping": {"status": "DEFECT"}
      }
    },
    {
      "name": "Log to Events",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "append",
        "sheet": "Events",
        "mapping": {
          "item_number": "={{ $json.prm }}",
          "event_type": "STATUS_CHANGE",
          "new_status": "={{ $node['Route by Button'].json.new_status }}",
          "actor": "={{ $json.from }}",
          "message_id": "={{ $json.message_id }}",
          "timestamp": "={{ $now }}",
          "telegram_chat_id": "={{ $json.chat_id }}"
        }
      }
    },
    {
      "name": "Reply Telegram",
      "type": "n8n-nodes-base.telegram",
      "parameters": {
        "text": "✅ Принято: {{ $json.prm }} → {{ $json.new_status }}. Записано в Sheet.",
        "chatId": "={{ $json.chat_id }}",
        "additionalFields": {
          "reply_markup": "{"inline_keyboard": [[{"text": "✅ Приняла PRM-...", "callback_data": "Приняла PRM-2026-0001"}, {"text": "✅ Готово", "callback_data": "Готово PRM-2026-0001"}, {"text": "⚠️ Брак", "callback_data": "Брак PRM-2026-0001"}]]}"
        }
      }
    }
  ]
}
```

#### Настройка credentials:
- Telegram API → вставь токен из BotFather
- Google Sheets OAuth2 → подключи Google аккаунт с таблицей

### Логика 3 кнопок:

1. Швея получает фото от оператора с подписью `PRM-2026-0001 Платье шелк пятно`
2. Под фото 3 inline-кнопки:
   - `✅ Приняла` → Orders.status = ACCEPTED / WITH_MASTER, Events LOG
   - `✅ Готово` → Orders.status = READY, Events LOG + уведомление клиенту (шаблон)
   - `⚠️ Брак` → Orders.status = DEFECT, Events LOG + фото брака

3. Idempotency: 
   - Каждое нажатие имеет message_id (уникальный ID сообщения Telegram)
   - Перед записью n8n делает Lookup в листе Events по message_id
   - Если уже есть → STOP, не дублируем
   - Если нет → пишем

Это защита от двойного тапа швеи и от повторной отправки Telegram.

### Вариант B — Make.com (Integromat) — еще проще без JSON

1. Scenario: Telegram Bot → Watch Updates
2. Router → 3 фильтра по Text contains "Приняла", "Готово", "Брак"
3. Google Sheets → Search Rows: Events where message_id = MessageID
4. Filter: если найдено 0 → продолжаем, если >0 → стоп
5. Google Sheets → Update Row: Orders где item_number = PRM-xxxx
6. Google Sheets → Add Row: Events
7. Telegram → Send Message: подтверждение

## Шаг 4 — Тест PRM-2026-0001

1. Создай заказ PRM-2026-0001 в Orders → NEW
2. Отправь в чат швеи: `PRM-2026-0001`
3. Бот должен ответить 3 кнопками
4. Нажми `Приняла` → проверь Orders стал ACCEPTED
5. Нажми еще раз `Приняла` (дубль) → должен сказать "уже принято", в Events не должно быть дубля
6. Нажми `Готово` → READY
7. Нажми `Брак` → DEFECT (ветка)

## Сообщения клиенту — авто из n8n

После READY → n8n может слать WhatsApp/Telegram клиенту через шаблон (см Шаблоны/Шаблон_Сообщений_Клиенту.md)

## Бюджет
- BotFather: 0
- n8n Cloud Free: 0 (до 5000 выполнений)
- Make Free: 0 (1000 ops)
- Google Sheets API: 0

Итого: 0 ₽

## SOP Приемка
Соответствует SOP_Приемка_QR.md из TASK_006: QR + 3 кнопки = приемка без приложения.
