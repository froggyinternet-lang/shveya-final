# 00_README_КУДА_РАЗЛОЖИТЬ — Concierge MVP без сервера за 1 день
**EXECUTOR_007 ФИНАЛ | SHVEYA.md v2.4 | Бюджет <6.5K ₽**

## Цель
Запустить Concierge MVP без сервера, без приложения, без программистов.
Только: Google Sheet (10 листов) + Telegram бот (3 кнопки) + QR Google Chart API + печать 30x20мм.

## Куда разложить ZIP:
```
TASK_007_ALL/
├── 00_README_КУДА_РАЗЛОЖИТЬ.md  <- ты здесь
├── Concierge/
│   ├── Google_Sheet_Структура.md
│   ├── Google_Sheet_Формулы.md
│   ├── Telegram_Бот_Без_Кода.md
│   ├── QR_Без_Кода.md
│   └── Чеклисты_Concierge/
│       ├── Чеклист_Оператор.md
│       ├── Чеклист_Курьер.md
│       └── Чеклист_Швея.md
├── Шаблоны/
│   ├── Order_Template.xlsx
│   ├── Nakladnaya_QR_Template.docx
│   ├── Шаблон_Сообщений_Клиенту.md
│   ├── Наклейка_30x20_шаблон.html
│   └── Пример_Заказ_PRM-2026-0001.csv
└── MANIFEST.json
```

## Запуск за 1 день — 5 шагов (4 часа работы)

### Шаг 1 — Google Sheet (60 мин) [Бесплатно]
1. Создай новую Google Таблицу: `SHVEYA Concierge PROD`
2. Создай 10 листов из файла `Concierge/Google_Sheet_Структура.md` — скопируй заголовки 1:1
3. Вставь формулы из `Concierge/Google_Sheet_Формулы.md`
4. Защити листы: Данные → Защитить листы → кроме оператора
5. Включи историю версий.

Структура DDL взята из `migrations/001_initial_final.sql` (TASK 004). Поля — 1:1.

### Шаг 2 — Telegram Бот без кода (30 мин) [Бесплатно]
1. Открой @BotFather в Telegram → /newbot → имя `SHVEYA Concierge Bot`
2. Сохрани токен: `123456:ABC...`
3. Открой n8n.cloud (бесплатный) или Make.com
4. Импортируй workflow из `Concierge/Telegram_Бот_Без_Кода.md` — там JSON для n8n.
5. 3 кнопки: `✅ Приняла`, `✅ Готово`, `⚠️ Брак`
6. Каждая кнопка пишет в Google Sheet + проверка idempotency по MessageID (защита от дублей).

### Шаг 3 — QR без кода (20 мин) [Бесплатно]
- Формула QR: `https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=PRM-2026-0001`
- Где `chl=` — твой `item_number` из Orders.
- Генерация в Google Sheet: `=IMAGE("https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl="&A2)` где A2 = PRM-2026-0001
- Печать: смотри `Concierge/QR_Без_Кода.md` и `Шаблоны/Наклейка_30x20_шаблон.html`

### Шаг 4 — Печать 30x20мм (30 мин) [~500₽ за 500шт]
1. Открой `Шаблоны/Наклейка_30x20_шаблон.html` в браузере → Печать → Размер 30x20мм
2. Принтер: любой термопринтер (Xprinter 365B) или обычный лазер + самоклейка А4 65 наклеек/лист (разрезать).
3. На наклейке: QR + PRM-2026-0001 + Клиент + Тип изделия.

SOP Приемки QR из TASK_006 — уже соблюден: QR клеится на пакет + дублируется в накладной.

### Шаг 5 — Чеклисты и Шаблоны (60 мин)
1. Распечатай 3 чеклиста из `Concierge/Чеклисты_Concierge/` — повесь на стену.
2. Распечатай `Шаблоны/Nakladnaya_QR_Template.docx` — 10 штук для курьера.
3. Скопируй сообщения клиенту из `Шаблоны/Шаблон_Сообщений_Клиенту.md` в WhatsApp Business быстрые ответы.

## Бюджет <6.5K — разбивка:
- Google Workspace: 0 ₽ (бесплатный аккаунт)
- Telegram Bot: 0 ₽
- n8n Cloud Free / Make Free: 0 ₽ (до 1000 операций)
- Google Chart QR API: 0 ₽
- Печать 500 наклеек 30x20 термо: 500-800 ₽
- Папка/пакеты с QR-окном: 1200 ₽
- Резерв на сим/интернет курьеру: 1000 ₽
- ИТОГО: ~2700 ₽ < 6500 ₽ — уложились.

## Idempotency — защита от дублей
В листе Events колонка `message_id` (Telegram message_id). Формула: если такой message_id уже есть → не писать повторно.
В n8n: IF node → Google Sheets Lookup → message_id exists? → Stop.

## Статусы (из DDL 004):
NEW → ACCEPTED → IN_TRANSIT_TO_MASTER → WITH_MASTER → READY → IN_TRANSIT_TO_CLIENT → DELIVERED
Ветка брака: WITH_MASTER → DEFECT → NEW (повтор)

## Готово к сдаче:
После настройки сделай тестовый заказ PRM-2026-0001, проведи по всем статусам 3 кнопками, сфоткай наклейку 30x20 — это приемка по SOP_Приемка_QR.md

---
TASK_007 | EXECUTOR_007 | CONTEXT.md 006 DONE 11/11 → 007 START
