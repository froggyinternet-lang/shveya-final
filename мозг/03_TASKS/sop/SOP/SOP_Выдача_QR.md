# SOP_Выдача_QR — Скан QR + фото-подтверждение

**Версия:** v1.0 TASK_006 | Rule 4 photo_url NOT NULL | TASK_011 проверка перепутана 7

### Цель
Выдать правильную вещь правильному клиенту с фото-доказательством. Нулевая пересортица.

### Триггер
Клиент пришел / курьер return CHECK IN.

### Шаг 1 — Скан QR
- Сканировать наклейку QR сканером/телефоном.
- Система ищет `items WHERE item_number = 'PRM-2026-0001'`
- Если не читается: ввести руками PRM-2026-0001, проверить по фото artifacts.

### Шаг 2 — Проверка перепутана (7 проверок из TASK_011)
Перед выдачей ОБЯЗАТЕЛЬНО:
1. item_number на наклейке == item_number в системе?
2. item_number на пакете == item_number на вещи?
3. Фото front/back из приемки совпадает с вещью визуально?
4. measurements совпадают?
5. Клиент ФИО / телефон совпадает с заказом?
6. Статус State Machine = ГОТОВО? (нельзя выдавать из ПРИЕМКА/В_РАБОТЕ/БРАК)
7. Нет второй вещи с похожим номером (PRM-2026-0001 vs PRM-2026-0010) в зоне выдачи?

Если хоть один FAIL → СТОП, позвать старшего.

### Шаг 3 — Фото return_confirmations (Rule 4)
Таблица (из 001_initial_final.sql):
```sql
CREATE TABLE return_confirmations (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id) NOT NULL,
  photo_url TEXT NOT NULL, -- Rule 4: NOT NULL
  customer_confirmed BOOLEAN DEFAULT false,
  confirmed_at TIMESTAMPTZ,
  created_by TEXT NOT NULL
);
```
- Сделать фото: вещь + пакет + QR в кадре. Идеально + клиент (с согласия) или рука клиента принимающая.
- photo_url NOT NULL — без фото кнопка Выдать заблокирована.
- Загрузить в S3 / локально, записать URL.

### Шаг 4 — customer_confirmed
- Клиент осмотрел, претензий нет → чекбокс customer_confirmed = true
- Клиент подписал (ЭЦП/на экране) → confirmed_at = now()

### Шаг 5 — transfer_history
```sql
INSERT INTO transfer_history (item_id, from_stage, to_stage, actor)
VALUES (<id>, 'ГОТОВО', 'ВЫДАНО', 'vydacha_maria');
```

### Шаг 6 — State Machine
ГОТОВО → ВЫДАНО (финальное). Откат только через старшего с event БРАК_ВОЗВРАТ.

### Исключения
- QR поврежден → поиск по номеру + фото сверка
- Клиент не тот → отказ, запись в events type='wrong_customer_attempt'
- Вещь не готова → извинение, новый срок, запись в transfer_history to='ОЖИДАНИЕ'

### DoD
- [ ] QR отсканирован
- [ ] 7 проверок перепутана пройдены
- [ ] Фото return_confirmations загружено (photo_url NOT NULL)
- [ ] customer_confirmed = true
- [ ] transfer_history записан
