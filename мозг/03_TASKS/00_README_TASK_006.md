# TASK_006 — КУДА РАЗЛОЖИТЬ + КАК ПЕЧАТАТЬ QR

## Куда разложить
Скопировать содержимое ZIP в:
```
C:\Perm_Repair\мозг\03_TASKS\sop\
```
Структура в репо:
- мозг/03_TASKS/sop/SOP_Приемка_QR.md
- мозг/03_TASKS/sop/SOP_Выдача_QR.md
- мозг/03_TASKS/sop/SOP_Швея_3_кнопки.md
- мозг/03_TASKS/sop/SOP_Курьер_2_плеча.md
- мозг/03_TASKS/sop/Чеклисты/
- мозг/03_TASKS/sop/QR/

## Как печатать QR
1. QR формат: см. QR/QR_Формат_PRM-2026-0001.md — payload = `PRM-2026-0001`
2. Принтер: термотрансфер 203dpi, лента 30x20 мм, водостойкая.
3. Шаблон: QR/QR_Печать_Шаблон.md — есть ZPL и HTML.
4. Печать из админки: /admin/items/PRM-2026-0001/qr — кнопка Печать.
5. Клеить: на внутренний шов/петлю, не на лицевую ткань. Дублировать в пакет.
6. Тест скана: телефоном + сканером на приемке. Если не читается — перепечатать.

## Зависимости (из CONTEXT.md 005 DONE 7/7 + State_Machine.md 004 + 001_initial_final.sql)
- Rule 7 SHVEYA.md v2.4: item_number UNIQUE, формат PRM-YYYY-NNNN, пример PRM-2026-0001
- Rule 4: return_confirmations.photo_url NOT NULL — выдача без фото запрещена
- transfer_history — immutable, append-only
- events.idempotency_key UNIQUE

## Проверка после раскладки
- [ ] Все 4 SOP на месте
- [ ] 3 чек-листа в Чеклисты/
- [ ] QR формат совпадает с DDL
- [ ] Печать теста 1 наклейки PRM-2026-0001

Бюджет: <6.5K токенов, ZIP один.
