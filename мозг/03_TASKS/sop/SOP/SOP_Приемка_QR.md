# SOP_Приемка_QR — Приемка с QR и 5 фото

**Версия:** v1.0 TASK_006 | SHVEYA.md v2.4 Rule 7 | State: ПРИЕМКА

### Цель
Завести вещь в систему с уникальным item_number PRM-2026-0001, 5 фото-доказательствами, замерами, QR-маркировкой.

### Триггер
Клиент принес вещь в пункт / курьер pickup CHECK IN.

### Оборудование
Телефон с камерой, вешалка однотонная, линейка, принтер наклеек 30x20, сканер QR.

### Формат item_number (Rule 7)
`PRM-YYYY-NNNN` — Regex `^PRM-\d{4}-\d{4}$`
Пример: PRM-2026-0001
Генерация: `SELECT nextval('item_seq')` → формат в коде. UNIQUE constraint в 001_initial_final.sql

### Шаг 1 — Создание карточки
- garment_types 6 (enum в DDL): 
  1. куртка 2. пальто 3. пуховик 4. шуба 5. дубленка 6. парка
- Ввести: тип, цвет, бренд, дефект словами.

### Шаг 2 — 5 фото artifacts (ОБЯЗАТЕЛЬНО, иначе блок приемки)
Таблица `artifacts`:
```sql
CREATE TABLE artifacts (
  id UUID PRIMARY KEY,
  item_id UUID REFERENCES items(id),
  photo_url TEXT NOT NULL,
  type TEXT CHECK (type IN ('front','back','defect_close','label','fabric')),
  created_at TIMESTAMPTZ DEFAULT now()
);
```
Чек:
1. front — спереди целиком на вешалке
2. back — сзади целиком
3. defect_close — дефект крупно + линейка
4. label — бирка бренда/размер
5. fabric — состав, износ, подкладка

Каждое фото <10MB, хорошее освещение, без других вещей в кадре.

### Шаг 3 — measurements 6
Таблица `measurements`:
- chest (грудь)
- waist (талия)
- hips (бедра)
- length (длина изделия)
- sleeve (рукав)
- shoulder (плечо)
Все в см, integer. Если неприменимо — NULL + причина.

### Шаг 4 — QR наклейка PRM-2026-0001
- Печать из QR/QR_Печать_Шаблон.md
- Payload: `PRM-2026-0001` (plain) или URL `https://perm.local/i/PRM-2026-0001`
- Клеить внутрь, сфоткать как proof что наклеена (6-е фото опционально но рекомендуется)

### Шаг 5 — transfer_history immutable
```sql
INSERT INTO transfer_history (item_id, from_stage, to_stage, actor, created_at)
VALUES (<id>, 'NEW', 'ПРИЕМКА', 'priemshik_ivan', now());
```
Никаких UPDATE/DELETE. Только INSERT.

### Шаг 6 — Проверка Definition of Done
- [ ] item_number = PRM-2026-0001 валиден по regex
- [ ] 5 фото в artifacts
- [ ] 6 замеров (или NULL с причиной)
- [ ] QR напечатан и наклеен
- [ ] transfer_history запись создана
- [ ] State Machine: NEW → ПРИЕМКА

### Антипаттерны
- 1 фото вместо 5 — ЗАПРЕТ
- QR без item_number — ЗАПРЕТ
- Замеры на глаз — ЗАПРЕТ, только рулетка
