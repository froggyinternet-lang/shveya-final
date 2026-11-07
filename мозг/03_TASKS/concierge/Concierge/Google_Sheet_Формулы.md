# Google Sheet Формулы — Concierge MVP без кода

## 1. Генерация item_number = PRM-YYYY-NNNN (Ключевая формула)

### Вариант A — английский Sheets:
В Orders!B2 (item_number):
```
="PRM-"&YEAR(TODAY())&"-"&TEXT(ROW()-1,"0000")
```
Результат: PRM-2026-0001, PRM-2026-0002...

### Вариант B — русский интерфейс:
```
="PRM-"&ГОД(СЕГОДНЯ())&"-"&ТЕКСТ(СТРОКА()-1;"0000")
```

### Вариант C — стабильный без TODAY (рекомендуется для продакшн):
Чтобы номер не менялся при смене года, зафиксируй год создания:
В C2 created_at: `=NOW()`
В B2:
```
="PRM-"&YEAR(C2)&"-"&TEXT(ROW()-1,"0000")
```

### Вариант D — с префиксом зоны:
```
="PRM-"&YEAR(TODAY())&"-"&VLOOKUP(F2;Zones!A:B;2;0)&"-"&TEXT(ROW()-1,"0000")
```
Где F2 = zone_id

## 2. QR URL без кода
В Orders!L2 (qr_url):
```
="https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl="&B2
```
Где B2 = PRM-2026-0001

В M2 картинка QR (опционально):
```
=IMAGE("https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl="&B2)
```

## 3. Статусы NEW → DELIVERED + цвета (Conditional Formatting)

### Статусы:
```
NEW — только создан
ACCEPTED — оператор приняла (кнопка 1)
IN_TRANSIT_TO_MASTER — у курьера к швее
WITH_MASTER — у швеи
READY — готово (кнопка 2)
IN_TRANSIT_TO_CLIENT — у курьера к клиенту
DELIVERED — доставлено клиенту
DEFECT — брак (кнопка 3)
CANCELLED — отменен
```

### Авто-подсчет deadline:
В G2 deadline_at:
```
=C2+3
```
+3 дня. Формат Дата.

Или рабочие дни:
```
=WORKDAY(C2;3)
```

### Просрочка:
В N2 is_overdue:
```
=IF(AND(G2<TODAY();NOT(E2="DELIVERED")); "⚠️ ПРОСРОЧКА"; "")
```

### Баланс:
В K2 balance:
```
=H2-I2
```
total_price - prepayment

### Авто-клиент имя:
В Orders!O2 client_name:
```
=VLOOKUP(C2;Clients!A:B;2;FALSE)
```

### Авто-мастер по специализации:
В Transfers! мастер:
```
=VLOOKUP(B2;Garments!A:E;5;0) — ищем fabric → подбираем мастера
```

## 4. Events + Idempotency через MessageID (защита от дублей)

В Events!J2 message_id приходит из Telegram бота.

Формула проверки дубля в Orders! при записи через n8n:
Логика в n8n (не в Sheets):
```
1. Google Sheets Lookup: Искать в Events message_id = {{$json.message_id}}
2. IF: если найдено >0 → STOP (дубль)
3. Если не найдено → писать новое событие
```

В Sheets для ручной проверки дубля:
В Events!L2 is_duplicate:
```
=IF(COUNTIF(J:J;J2)>1;"ДУБЛЬ";"OK")
```
Conditional Formatting: если ДУБЛЬ → красный фон.

## 5. Счетчики для дашборда (отдельный лист Dashboard)

Создай лист Dashboard:
```
A1: Всего заказов =COUNTA(Orders!B:B)-1
A2: NEW =COUNTIF(Orders!E:E;"NEW")
A3: WITH_MASTER =COUNTIF(Orders!E:E;"WITH_MASTER")
A4: READY к выдаче =COUNTIF(Orders!E:E;"READY")
A5: DEFECT =COUNTIF(Orders!E:E;"DEFECT")
A6: Выручка сегодня =SUMIF(Payments!G:G;TODAY();Payments!D:D)
A7: Загрузка швеи Зарема =COUNTIF(Transfers!F:F;"1")
```

## 6. VLOOKUP связки (как JOIN без SQL)

Пример: в Orders показать телефон клиента:
```
=VLOOKUP(C2;Clients!A:C;3;FALSE)
```

## 7. Генерация накладной ссылки
В Orders!P2 nakladnaya_link:
```
="https://docs.google.com/document/d/.../export?item="&B2
```
Или просто:
```
=HYPERLINK("https://chart.googleapis.com/chart?chs=300x300&cht=qr&chl="&B2;"📄 Накладная "&B2)
```

## 8. Защита формулы item_number
Выдели столбец B → Данные → Защитить диапазон → Только ты можешь редактировать. Операторы не смогут испортить нумерацию.

## 9. Авто-сортировка NEW сверху
Данные → Создать фильтр → Сортировать по created_at DESC.

Готово. Этих формул достаточно для MVP без сервера.
