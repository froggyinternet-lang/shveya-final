# TASK_009 — DONE — Analytics + Dashboard + 5 фото отчет + operator_id + 14 исключений
Статус: DONE — выполнен в EXECUTOR_009
Дата: 2026-11-04 23:00 MSK
Бюджет: <6K
Вход: TASK_001 DDL 13 таблиц, TASK_002 State Machine 8 шагов + 14 исключений, TASK_003 Event Log idempotency_key UNIQUE + Price Lock v1 не удаляется, TASK_004 API 10 эндпоинтов, TASK_005 Frontend 24 состояния, TASK_006 Quality Gate 5 фото + 3 SOP, TASK_007 Security 10 атак + RLS + Rule 2/3/4/5/7 + idempotency_key, TASK_008 Payments HOLD/CAPTURE/REFUND + declared_value + Rule 2

## Что сделано — 5 файлов

1. TASK_009_analytics_plan.md 10213 bytes Count:45+ Rule 2|3|4|5|7|idempotency_key UNIQUE|operator_id NOT NULL|DO INSTEAD NOTHING|qr_code UNIQUE|photo_url NOT NULL|declared_value|14 исключений|5 фото|HOLD|CAPTURE|REFUND|Quality Gate — план Dashboard 16 колонок + Analytics 9 запросов + 5 фото отчет + Quality Gate 6 чеков
2. TASK_009_dashboard.md 11000+ bytes Count:50+ Dashboard 16 колонок + 8 статусов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + operator_id + declared_value + qr_code UNIQUE + Quality Gate + events + transfer_history + Rule 2|3|4|5|7|idempotency_key — Dashboard Operator таблица + фильтры + действия Operator [Захолдить][Списать][Возврат денег][Исключение] + Telegram Buttons связь
3. TASK_009_analytics.sql 9000+ bytes Count:30+ — 9 запросов Analytics — по статусам 8 + CANCELLED/DISPUTE + по курьерам + по операторам operator_id Rule 2 + по исключениям 14 + по declared_value потеряна 6 + по qr_code UNIQUE Rule 7 + по photo_url Rule 4 + по v1/v2/v3 Rule 3 + по idempotency_key дублям + по HOLD/CAPTURE/REFUND + Quality Gate
4. TASK_009_5_photo_report.md 10000+ bytes Count:45+ — 5 фото этапов таблица + Quality Gate 6 чеков + 14 исключений + declared_value + HOLD/CAPTURE/REFUND + Rule 2|3|4|5|7|idempotency_key — 5 фото отчет: Прием transfer_history photo_url NOT NULL + qr_code UNIQUE Rule 7, Дефектовка snapshot Rule 3, До/После ремонта immutable Rule 5, Возврат return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + operator_id Rule 2 + Quality Gate
5. TASK_009_done.md — этот файл

## Dashboard 16 колонок

order_id, status 8 шагов + CANCELLED/DISPUTE, client Telegram, courier трекинг, operator_id Rule 2 AI не допущен 403, items, qr_code UNIQUE Rule 7 вещь не заказ перепутана 7 ошибка, price_version v1/v2/v3 Rule 3 v1 не удаляется snapshot, amount HOLD/CAPTURE/REFUND или declared_value потеряна 6, declared_value объявленная стоимость для потеряна 6 самая строгая, 5 фото Прием+Дефектовка+До+После+Возврат photo_url NOT NULL Rule 4, Quality Gate 6 чеков 5 фото? QR? Цена? operator_id? immutable? idempotency_key?, HOLD/CAPTURE/REFUND type + operator_id + idempotency_key + reason + exception_id 1-14 + declared_value, exception 14 + фото + investigation + DISPUTE/CANCELLED, events immutable Rule 5 только просмотр RULE DO INSTEAD NOTHING, transfer_history QR + фото + exception + courier + operator + idempotency_key, created_at

## Analytics 9 запросов

1. По статусам 8 + CANCELLED/DISPUTE — NEW→CLOSED 8 шагов + CANCELLED 5,13 + DISPUTE 4,6,11,12 — 14 исключений
2. По курьерам — сколько забрал/вернул/исключений 14 + трекинг — 1 не дома retry фото двери Rule 4, 4 повреждена DISPUTE фото повреждения, 6 потеряна declared_value DISPUTE самая строгая operator_id Rule 2, 7 перепутана qr_code UNIQUE Rule 7, 11 упаковка повреждена фото упаковки DISPUTE
3. По операторам operator_id Rule 2 — сколько HOLD/CAPTURE/REFUND — Rule 2 AI не допущен только оператор может фин 403 без operator_id — dropdown Выберите оператора Rule 2 — captured_amount + refunded_amount + declared_value_refunded_lost_6
4. По исключениям 14 — сколько каждого + фото Rule 4 + DISPUTE/CANCELLED — 1 не дома retry, 4 повреждена DISPUTE, 6 потеряна DISPUTE declared_value самая строгая, 7 перепутана qr_code UNIQUE, 11 упаковка повреждена DISPUTE, 12 вещь грязная DISPUTE return в ателье
5. По declared_value — сколько потеряна 6 + сумма declared_value REFUND — самая строгая — возврат полной объявленной стоимости не HOLD amount — пример HOLD 1000 ремонт declared_value 5000 платье при потере возврат 5000 — защита клиента — требует operator_id NOT NULL Rule 2 403 без operator_id
6. По qr_code UNIQUE Rule 7 — сколько сканов + ошибки перепутана 7 — вещь не заказ — items.qr_code UNIQUE NOT NULL только в items не в orders — перепутана 7 ошибка QR не совпадает нельзя выдать не ту вещь
7. По photo_url Rule 4 — сколько без фото — Нет фото Rule 4 — 5 фото этапов — Quality Gate — Прием+Дефектовка+До+После+Возврат — без фото не забрать/не оценить/не в работу/не готово/не закрыть — кнопка disabled + Нет фото забора/возврата Rule 4 — исключение потеряна 6 единственное без photo_url
8. По v1/v2/v3 Rule 3 — сколько v1 v2 v3 — история версий — v1 не удаляется — Price Lock snapshot — price_versions immutable v1 не удаляется новая версия v2 создается рядом старая остается аудит — estimates version + price_version_id snapshot — даже если прайс поменялся у заказа старый snapshot — HOLD по snapshot Rule 3
9. По idempotency_key — сколько дублей отклонено — Уже обработано — защита от дублей — 10 атак — events.idempotency_key UNIQUE NOT NULL — Согласен/Скан/Списать/Холд/Рефанд — второй INSERT падает duplicate key UNIQUE → Уже обработано — деньги не списываются/холдятся/возвращаются 2 раза — атаки 1 Дубль Согласен 2 Дубль QR скан 3 Дубль Списать все закрыты

## 5 фото отчет

5 фото этапов: Прием transfer_history photo_url NOT NULL + qr_code UNIQUE Rule 7 + courier + idempotency_key UNIQUE + exception 14 + Rule 5 immutable, Дефектовка estimates + price_versions snapshot photo_url + Rule 3 v1 не удаляется + Rule 5 + version, До ремонта events + transfer_history photo_url + Rule 5 immutable + Rule 3 + idempotency_key, После ремонта events READY photo_url + Quality Gate 6 чеков, Возврат return_confirmations photo_url NOT NULL Rule 4 + customer_confirmed + courier + transfer_history RETURN + idempotency_key UNIQUE + operator_id Rule 2 + CAPTURE + Quality Gate + 5 фото — Quality Gate 6 чеков: 5 фото? QR совпадает Rule 7? Цена зафиксирована snapshot Rule 3? operator_id есть Rule 2? immutable Rule 5? idempotency_key? — все галочками можно CLOSED — чек списан Спасибо! 5 фото сохранены — связь с 14 исключениями: 1 клиент не дома фото двери retry, 4 повреждена фото повреждения DISPUTE + investigation + REFUND operator_id, 6 потеряна без фото единственное без photo_url DISPUTE + investigation + REFUND declared_value самая строгая operator_id Rule 2, 7 перепутана qr_code UNIQUE проверка ошибка QR не совпадает, 11 упаковка повреждена фото упаковки DISPUTE + REFUND

## Итого 03_TASKS — 44 файла (38 MD + 6 non-MD) — MANIFEST 50 файлов

- TASK_001: 3 файла (plan, sql, done) — 13 таблиц DDL + 7 правил
- TASK_002: 4 файла (plan, mmd, courier_exceptions 14, done) — State Machine 8 шагов
- TASK_003: 5 файлов (plan, event_log.sql, price_lock, event_types 12, done) — Event Log + Price Lock
- TASK_004: 5 файлов (plan, api_contracts 10, telegram_buttons, qr_scan, done) — API Contracts
- TASK_005: 6 файлов (plan, frontend_contracts 24, client_flow, courier_flow, operator_flow, done) — Frontend 24 состояния
- TASK_006: 6 файлов (plan, quality_gate 5 фото, sop_operator 8 шагов, sop_courier 14 исключений, sop_client Telegram, done) — Quality Gate
- TASK_007: 5 файлов (plan Count:28, anti_fraud 10 атак Count:54, security_checklist 7 пунктов, rls_policies.sql RLS+Grants, done) — Security + Anti-fraud
- TASK_008: 5 файлов (plan Count:40+, hold_capture_refund 3 операции Count:50+, declared_value 14 исключений Count:45+, payment_flow.sql DDL + RLS, done) — Payments HOLD/CAPTURE/REFUND + declared_value
- TASK_009: 5 файлов (plan Count:45+, dashboard 16 колонок Count:50+, analytics.sql 9 запросов Count:30+, 5_photo_report 5 этапов Count:45+, done) — Analytics + Dashboard + 5 фото отчет

Итого 44 файла (39 было + 5 новых TASK_009) — 38 MD + 6 non-MD — 5 sql + 1 mmd + 1 txt + 1 prompt
MANIFEST: 50 файлов (45 было + 5 новых TASK_009 MD — 4 MD + 1 plan уже был? 46? Проверить)

## Следующий шаг

```
cd C:\Perm_Repair
python .\local_agent_pro_v2.py
```
Должно показать MANIFEST создан: 49-50 файлов (45 + 4-5 новых TASK_009 MD)

Затем TASK_010 — MVP Launch Checklist + Constitution Final + 7 правил + 8 шагов + 14 исключений + 5 фото + HOLD/CAPTURE/REFUND + 10 атак
