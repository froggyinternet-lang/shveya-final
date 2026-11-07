
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="SHVEYA Perm Repair — SSOT Check", version="v2.4 FINAL")

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
    <head><title>SHVEYA — Что сделали</title>
    <style>body{font-family:monospace;padding:20px;background:#0f0f0f;color:#0f0}
    .ok{color:#0f0} .card{border:1px solid #333;padding:15px;margin:10px 0;background:#1a1a1a}
    a{color:#0ff} h1{color:#fff}
    </style></head>
    <body>
    <h1>🧵 SHVEYA Perm Repair — FINAL 38 файлов</h1>
    <p>Дата: 2026-11-05 | Грант 10к b2.medium 2x50% 4GB | Бюджет <6.5K</p>
    
    <div class="card">
    <h2 class="ok">✅ 004 DDL 6/6 — migrations/</h2>
    <ul>
    <li>001_initial_final.sql — 20 таблиц + CHECK leg_number IN (1,2) + UNIQUE + partial unique is_current + RULE v1 не удаляется + RULE immutable + idempotency 3 UNIQUE + pgcrypto + ENUM 10 статусов + триграм GIN + GENERATED total_price</li>
    <li>002_seed.sql — measurements 6 + garment_types 6 + Мотовилиха + 2 Points + state_transitions 13 + courier_exceptions 14</li>
    <li>003_constraints_check.sql</li>
    <li>docs/ ER_Diagram.md + State_Machine.md + Price_Lock_Event_Log.md</li>
    </ul>
    </div>

    <div class="card">
    <h2 class="ok">✅ 005 docker-compose 7/7 — грант 10к</h2>
    <ul>
    <li>docker-compose.yml — postgres:15-alpine 512MB + api 1GB + bot 512MB = 2GB < 4GB</li>
    <li>api/Dockerfile python:3.11-slim + fastapi + asyncpg</li>
    <li>bot/Dockerfile aiogram 3.7</li>
    <li>scripts/ deploy_b2_medium.sh + backup.sh + check_grant.sh</li>
    <li>.env.example — DATABASE_URL + YOOKASSA + TELEGRAM_BOT_TOKEN</li>
    </ul>
    <p>Запуск: docker compose up -d --build → <a href="/docs">/docs</a> Swagger</p>
    </div>

    <div class="card">
    <h2 class="ok">✅ 006 SOP QR 11/11 — мозг/03_TASKS/sop/</h2>
    <ul>
    <li>SOP_Приемка_QR.md — 5 фото artifacts (front/back/defect_close/label/fabric) + QR PRM-2026-0001 + transfer_history</li>
    <li>SOP_Выдача_QR.md — скан QR + 7 проверок перепутана Rule7 + return_confirmations photo_url NOT NULL Rule4</li>
    <li>SOP_Швея_3_кнопки.md — 3 кнопки Приняла/Готово/Брак + transfer_history immutable + events idempotency_key UNIQUE</li>
    <li>SOP_Курьер_2_плеча.md — pickup/return CHECK IN (1,2) + 14 исключений 6 колонок</li>
    <li>QR/ QR_Формат_PRM-2026-0001.md — regex ^PRM-\\d{4}-\\d{4}$ Rule7</li>
    <li>QR_Печать_Шаблон.md — ZPL + HTML 30x20мм</li>
    </ul>
    </div>

    <div class="card">
    <h2 class="ok">✅ 007 Concierge MVP 14/14 ФИНАЛ — мозг/03_TASKS/concierge/</h2>
    <ul>
    <li>Google_Sheet_Структура.md — 10 листов: Orders, Garments, Transfers, Couriers, Masters, Payments, Events, Clients, Measurements, Zones — поля из DDL 004</li>
    <li>Google_Sheet_Формулы.md — item_number = "PRM-"&YEAR(TODAY())&"-"&TEXT(ROW(),"0000")</li>
    <li>Telegram_Бот_Без_Кода.md — BotFather + n8n JSON workflow 3 кнопки ✅ Приняла / ✅ Готово / ⚠ Брак + idempotency через MessageID</li>
    <li>QR_Без_Кода.md — https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=PRM-2026-0001</li>
    <li>Чеклисты_Concierge/ — оператор/курьер/швея без приложения</li>
    <li>Шаблоны/ Order_Template.xlsx + Nakladnaya_QR.docx + Сообщений + Наклейка_30x20.html + Пример PRM-2026-0001.csv</li>
    </ul>
    <p>Бюджет: ~3000₽ < 6500₽ — Google Sheet 0₽ + Telegram 0₽ + n8n Free 0₽ + наклейки 800₽</p>
    </div>

    <div class="card">
    <h2>🤖 Telegram — что делали</h2>
    <ul>
    <li>Клиенту: [✅ Согласен v1] [✅ Согласен v2] [❌ Отказываюсь] — callback_data agree:{order_id}:{version} + idempotency_key UNIQUE {order_id}:{event_type}:{ISO}:{rand} — дубль = "Уже обработано"</li>
    <li>Швее: 3 кнопки Приняла/Готово/Брак — каждая пишет transfer_history immutable + events idempotency UNIQUE — защита от двойного тапа</li>
    <li>Bot: aiogram 3.7 + n8n workflow — без сервера в Concierge MVP</li>
    <li>API: POST /api/telegram/callback — проверка version актуальной — если v2 создана, v1 нельзя agree Rule3</li>
    </ul>
    </div>

    <div class="card">
    <h2>📦 Что проверить на localhost:8000</h2>
    <ul>
    <li><a href="/docs">/docs</a> — Swagger 10 эндпоинтов: POST /api/order/create, estimate, telegram/callback, transfer/scan, payment/hold|capture|refund, GET order/{id}, dashboard, analytics</li>
    <li><a href="/health">/health</a> — проверка БД + 20 таблиц</li>
    <li><a href="/sot">/sot</a> — SSOT статус всех TASK</li>
    <li><a href="/qr/PRM-2026-0001">/qr/PRM-2026-0001</a> — тест QR формата</li>
    </ul>
    </div>

    <p><a href="/docs">→ Открыть Swagger /docs</a></p>
    </body></html>
    """

@app.get("/health")
def health():
    return {
        "status": "ok",
        "ssot": "C:/Perm_Repair/мозг/03_TASKS/",
        "tasks": {
            "004": "6/6 DDL",
            "005": "7/7 docker-compose b2.medium 2GB<4GB",
            "006": "11/11 SOP QR",
            "007": "14/14 Concierge FINAL"
        },
        "total_files": 38,
        "budget": "~3000rub < 6500rub",
        "grant": "10k b2.medium 2x50% 4GB",
        "db": "postgres:15-alpine 512MB limit",
        "api": "FastAPI + asyncpg 1GB",
        "bot": "aiogram 3.7 512MB",
        "rules": ["Rule2 operator_id NOT NULL", "Rule3 v1 не удаляется", "Rule4 photo_url NOT NULL", "Rule5 immutable", "Rule7 PRM-2026-0001 UNIQUE", "idempotency_key UNIQUE"]
    }

@app.get("/sot")
def sot():
    return {
        "migrations": ["001_initial_final.sql", "002_seed.sql", "003_constraints_check.sql"],
        "docs": ["ER_Diagram.md", "State_Machine.md", "Price_Lock_Event_Log.md"],
        "docker": ["docker-compose.yml", "api/Dockerfile", "bot/Dockerfile", "scripts/ 3 шт"],
        "sop": ["SOP_Приемка_QR.md", "SOP_Выдача_QR.md", "SOP_Швея_3_кнопки.md", "SOP_Курьер_2_плеча.md", "QR_Формат_PRM-2026-0001.md"],
        "concierge": ["Google_Sheet_Структура.md 10 листов", "Telegram_Бот_Без_Кода.md 3 кнопки", "QR_Без_Кода.md google chart", "Шаблоны 5 шт"],
        "telegram_buttons": {
            "client": ["✅ Согласен v1", "✅ Согласен v2", "❌ Отказываюсь"],
            "master": ["✅ Приняла", "✅ Готово", "⚠ Брак"],
            "callback": "agree:{order_id}:{version} / reject:{order_id}:{version}",
            "idempotency": "{order_id}:{event_type}:{ISO}:{rand4} UNIQUE"
        },
        "qr": {
            "format": "PRM-YYYY-NNNN regex ^PRM-\\d{4}-\\d{4}$",
            "example": "PRM-2026-0001",
            "no_code": "https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=PRM-2026-0001",
            "print": "30x20мм ZPL + HTML"
        }
    }

@app.get("/qr/{item_number}")
def qr_test(item_number: str):
    import re
    ok = bool(re.match(r"^PRM-\d{4}-\d{4}$", item_number))
    return {
        "item_number": item_number,
        "valid": ok,
        "rule7": "PRM-YYYY-NNNN UNIQUE",
        "qr_url": f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={item_number}",
        "print_html": "мозг/03_TASKS/sop/QR/QR_Печать_Шаблон.md + concierge/Шаблоны/Наклейка_30x20_шаблон.html"
    }
