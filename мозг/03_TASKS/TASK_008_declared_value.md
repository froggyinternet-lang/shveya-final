# TASK_008 — declared_value + 14 исключений — самая строгая потеряна 6
Дата: 2026-11-04
SSOT: SHVEYA.md v2.3 + TASK_002 14 исключений + TASK_007 Security 10 атак + TASK_008 HOLD/CAPTURE/REFUND

## declared_value — объявленная стоимость вещи — для потеряна 6

Поле: orders.declared_value INT NOT NULL — объявляется при создании заказа NEW — например платье 5000 руб declared_value=5000 — если курьер теряет вещь исключение 6 — возврат declared_value полностью — самая строгая защита клиента

### Когда используется declared_value

Только исключение 6 потеряна — вещь потеряна курьером/ателье — ничего нет — фото нет — только DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id NOT NULL Rule 2 — возврат полной объявленной стоимости — не HOLD amount, а declared_value — например HOLD 1000 руб ремонт, declared_value 5000 руб — при потере возврат 5000 руб, не 1000 руб

Для остальных исключений — возврат HOLD amount — ремонт не сделан/поврежден — возврат холда

## 14 исключений — таблица платежей

| # | Исключение | Тип | Что делать | amount | operator_id Rule 2 | photo_url Rule 4 | Что пишет | Telegram клиенту |
|---|---|---|---|---|---|---|---|---|
| 1 | клиент не дома | exception retry | HOLD остается — retry завтра — звонок клиенту + фото двери подъезда photo_url NOT NULL Rule 4 | HOLD amount остается | — | photo_url NOT NULL двери Rule 4 | transfer_history + events EXCEPTION_1 + exception 1 + retry + photo_url | "Клиент не дома — повтор завтра Фото двери" |
| 2 | адрес неверный | exception | HOLD остается — уточнить адрес + фото адреса | HOLD amount | — | photo_url NOT NULL адреса Rule 4 | exception 2 + photo_url | "Адрес неверный — уточните" |
| 3 | клиент перенес | exception reschedule | HOLD остается — reschedule + фото чата | HOLD amount | — | photo_url NOT NULL чата Rule 4 | exception 3 + reschedule + photo_url | "Клиент перенес — новая дата" |
| 4 | повреждена при заборе | DISPUTE investigation | DISPUTE + investigation + REFUND HOLD amount + operator_id NOT NULL Rule 2 — фото повреждения крупно обязательно Rule 4 | HOLD amount REFUND | operator_id NOT NULL Rule 2 | photo_url NOT NULL повреждения обязательно Rule 4 | DISPUTE + events DAMAGE + PAYMENT_REFUNDED operator_id Rule 2 + investigation + photo_url | "Повреждена при заборе — спор investigation — возврат HOLD" + фото |
| 5 | клиент отказался при доставке | CANCELLED | CANCELLED + REFUND HOLD amount + operator_id NOT NULL Rule 2 — фото вещи + отказ | HOLD amount REFUND | operator_id NOT NULL Rule 2 | photo_url NOT NULL вещи + отказ Rule 4 | CANCELLED 5 + PAYMENT_REFUNDED operator_id Rule 2 | "Отказан при доставке — возврат HOLD" |
| 6 | потеряна | DISPUTE investigation самая строгая | DISPUTE + investigation + REFUND declared_value — самая строгая — возврат полной объявленной стоимости — оператор только Rule 2 — 403 без operator_id — investigation — без фото | declared_value REFUND — не HOLD — полная стоимость вещи | operator_id NOT NULL Rule 2 самая строгая | — (ничего нет — потеряна) | DISPUTE + investigation + PAYMENT_REFUNDED declared_value + operator_id Rule 2 + events LOST + reason потеряна 6 | "Потеряна — спор investigation — возврат declared_value 5000 руб" — самая строгая защита клиента |
| 7 | перепутана | exception QR | HOLD остается — ошибка QR не совпадает Rule 7 — qr_code UNIQUE проверка в items — не тот QR — нельзя выдать — не тот заказ | HOLD amount остается | — | — (скан QR — проверка UNIQUE Rule 7) | ошибка "QR не совпадает — перепутана 7" — qr_code UNIQUE не совпадает Rule 7 — нельзя выдать | "Перепутана — QR не совпадает — проверка" |
| 8 | курьер опоздал | exception | HOLD остается — фото времени | HOLD amount | — | photo_url времени Rule 4 | exception 8 + photo_url | "Курьер опоздал — Фото времени" |
| 9 | дверь не открыли | exception retry | HOLD остается — 2 фото двери с интервалом 10 мин + фото Rule 4 + retry | HOLD amount | — | photo_url NOT NULL двери 2 раза Rule 4 | exception 9 + 2 photo_url двери | "Дверь не открыли — 2 фото — повтор" |
| 10 | клиент не отвечает | exception retry | HOLD остается — фото звонков скрин + retry | HOLD amount | — | photo_url звонков Rule 4 | exception 10 + retry + photo_url | "Клиент не отвечает — повтор" |
| 11 | упаковка повреждена | DISPUTE investigation | DISPUTE + investigation + REFUND HOLD amount + operator_id NOT NULL Rule 2 — фото упаковки обязательно Rule 4 | HOLD amount REFUND | operator_id NOT NULL Rule 2 | photo_url NOT NULL упаковки обязательно Rule 4 | DISPUTE + investigation + PAYMENT_REFUNDED operator_id Rule 2 + photo_url упаковки | "Упаковка повреждена — спор — возврат HOLD" + фото упаковки |
| 12 | вещь грязная после ремонта | DISPUTE return | DISPUTE + return в ателье — HOLD остается — фото грязи обязательно Rule 4 | HOLD amount остается | — | photo_url NOT NULL грязи Rule 4 | DISPUTE + return в ателье + photo_url | "Вещь грязная после ремонта — возврат в ателье" + фото |
| 13 | клиент передумал | CANCELLED | CANCELLED + REFUND HOLD amount + operator_id NOT NULL Rule 2 — фото вещи | HOLD amount REFUND | operator_id NOT NULL Rule 2 | photo_url NOT NULL вещи Rule 4 | CANCELLED 13 + PAYMENT_REFUNDED operator_id Rule 2 | "Клиент передумал — возврат HOLD" |
| 14 | форс-мажор | exception investigation | HOLD остается — exception 14 + investigation + фото ситуации | HOLD amount остается | — | photo_url ситуации Rule 4 | exception 14 + investigation + photo_url | "Форс-мажор — investigation" |

## Самая строгая — потеряна 6

- Только потеряна 6 возвращает declared_value, не HOLD amount
- Пример: заказ платье declared_value 5000 руб, ремонт 1000 руб HOLD — при потере возврат 5000 руб, не 1000 руб — защита клиента
- Требует operator_id NOT NULL Rule 2 — без оператора 403 — только оператор может вернуть declared_value — AI не допущен
- DISPUTE + investigation — расследование куда делась вещь — лог transfer_history immutable Rule 5 нельзя подделать — investigation
- Без фото — ничего нет — потеряна — единственное исключение без photo_url NOT NULL Rule 4
- idempotency_key UNIQUE — защита от дублей возврата declared_value — второй возврат declared_value падает duplicate key → Уже обработано

## Остальные — HOLD остается или REFUND HOLD amount

- 1,2,3,7,8,9,10,14 — HOLD остается — retry/reschedule/уточнить — не REFUND — вещь не потеряна/не повреждена — фото обязательно кроме 7
- 4,5,11,13 — DISPUTE/CANCELLED + REFUND HOLD amount + operator_id NOT NULL Rule 2 + photo_url NOT NULL Rule 4 — повреждена/отказался/упаковка/передумал — возврат холда
- 6 — DISPUTE + REFUND declared_value + operator_id NOT NULL Rule 2 — потеряна — самая строгая — возврат полной стоимости
- 12 — DISPUTE + return в ателье — HOLD остается — вещь грязная — переделать

## Связь с HOLD/CAPTURE/REFUND

- HOLD: при AGREED — холдится amount snapshot v1/v2 Rule 3 — declared_value отдельно — не холдится — только для потеряна 6
- CAPTURE: при CLOSED — списывается HOLD amount — требует return_confirmations photo_url NOT NULL Rule 4 + 5 фото + operator_id Rule 2 + Quality Gate
- REFUND: при CANCELLED/DISPUTE — возвращается HOLD amount или declared_value если потеряна 6 — требует operator_id NOT NULL Rule 2 + reason + idempotency_key UNIQUE + photo_url если есть Rule 4
