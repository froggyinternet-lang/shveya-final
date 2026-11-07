# Google Sheet Структура — 10 листов из DDL 004 (001_initial_final.sql)

> Создай Google Таблицу `SHVEYA Concierge PROD`. Создай 10 листов точно с такими заголовками. Первая строка — заголовки, вторая — пример PRM-2026-0001.

## 1. Лист `Orders` — Заказы (главный)
| Поле | Тип | Пример | Коммент из DDL |
|------|-----|--------|----------------|
| order_id | UUID / INT | 1 | PK, авто |
| item_number | TEXT UNIQUE | PRM-2026-0001 | `PRM-YYYY-NNNN` — генерируется формулой, см Формулы.md |
| client_id | FK → Clients | 1 | |
| garment_id | FK → Garments | 1 | 1 заказ = 1 изделие в MVP |
| status | ENUM | NEW | NEW, ACCEPTED, IN_TRANSIT_TO_MASTER, WITH_MASTER, READY, IN_TRANSIT_TO_CLIENT, DELIVERED, DEFECT, CANCELLED |
| created_at | DATETIME | 2026-05-13 10:00 | `=NOW()` |
| deadline_at | DATE | 2026-05-16 | +3 дня по дефолту |
| zone_id | FK → Zones | 1 | |
| total_price | INT | 1500 | |
| prepayment | INT | 500 | |
| balance | FORMULA | 1000 | =total-prepayment |
| operator_name | TEXT | Айгуль | |
| qr_url | FORMULA | https://...PRM-2026-0001 | `="https://chart...&chl="&B2` |
| notes | TEXT | пятно на рукаве | |
| telegram_message_id | TEXT | 12345 | для idempotency |

## 2. Лист `Garments` — Изделия
| garment_id | order_id | item_number | type | fabric | color | defect_desc | photo_url | measurement_id | status |
| 1 | 1 | PRM-2026-0001 | Платье | Шелк | Черный | пятно | drive.google.com/... | 1 | WITH_MASTER |

Поля из DDL: garment_type ENUM: dress, pants, skirt, jacket, shirt

## 3. Лист `Transfers` — Перемещения (логистика без сервера)
| transfer_id | garment_id | item_number | from_stage | to_stage | courier_id | master_id | timestamp | signature_url | notes |
| 1 | 1 | PRM-2026-0001 | OPERATOR | MASTER | 1 | 2 | 2026-05-13 11:00 | | |

## 4. Лист `Couriers` — Курьеры
| courier_id | name | phone | telegram_id | telegram_username | zone_id | active | current_load |
| 1 | Рустам | +996... | 123456789 | @rustam | 1 | TRUE | 2 |

## 5. Лист `Masters` — Швеи / Мастера
| master_id | name | specialization | phone | telegram_id | workload | rating | active | avg_time_hours |
| 1 | Зарема | пятна/шелк | +996... | 987... | 3 | 4.9 | TRUE | 24 |

## 6. Лист `Payments` — Платежи
| payment_id | order_id | item_number | client_id | amount | type | method | date | status | receipt_url |
| 1 | 1 | PRM-2026-0001 | 1 | 500 | prepayment | cash | 2026-05-13 | PAID | |

type: prepayment, full, balance, refund

## 7. Лист `Events` — События / Аудит + Idempotency (ключевой лист для бота)
| event_id | order_id | item_number | garment_id | event_type | old_status | new_status | actor | actor_role | timestamp | message_id | telegram_chat_id |
| 1 | 1 | PRM-2026-0001 | 1 | STATUS_CHANGE | NEW | ACCEPTED | Айгуль | operator | 2026-05-13 10:05 | 10001 | |

event_type: STATUS_CHANGE, TRANSFER, PAYMENT, DEFECT. message_id — ключ idempotency: дубликат не пишется.

## 8. Лист `Clients` — Клиенты
| client_id | name | phone | telegram | address | zone_id | loyalty_level | total_orders | notes |
| 1 | Алия | +996... | @aliya | 7мкр 15/2 | 1 | GOLD | 5 | VIP, только Зарема |

## 9. Лист `Measurements` — Замеры
| measurement_id | client_id | garment_id | item_number | chest | waist | hips | length | sleeve | shoulders | notes | created_at |
| 1 | 1 | 1 | PRM-2026-0001 | 88 | 68 | 92 | 110 | 60 | 40 | ушить на 1см | 2026-05-13 |

## 10. Лист `Zones` — Зоны доставки
| zone_id | name | city | delivery_price | courier_id | time_slot | active |
| 1 | Центр | Бишкек | 150 | 1 | 10-18 | TRUE |
| 2 | 7мкр | Бишкек | 200 | 1 | 10-18 | TRUE |

## Связи (как в SQL, но в Sheets через VLOOKUP)
- Orders.client_id → Clients.client_id =VLOOKUP(C2;Clients!A:B;2;0)
- Orders.garment_id → Garments.garment_id
- Transfers.courier_id → Couriers.courier_id

## Защита и валидация (Data Validation)
- Orders.status → Список: NEW,ACCEPTED,IN_TRANSIT_TO_MASTER,WITH_MASTER,READY,IN_TRANSIT_TO_CLIENT,DELIVERED,DEFECT,CANCELLED
- Все *_id → Число >0
- qr_url → должен содержать PRM-

## Пример строки для PRM-2026-0001 уже в Шаблоны/Пример_Заказ_PRM-2026-0001.csv
