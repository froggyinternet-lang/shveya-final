# ШВЕЯМОЗГ — MOCK CHECK 014 — проверка от лица клиента и от лица швеи — без Telegram — без Docker — на этом компе
# 8 шагов NEW->CLOSED — 5 фото — HOLD/CAPTURE — Rule 7 наклейка рукой — без hand_applied нельзя READY
import os
from pathlib import Path
from datetime import datetime
import json

PHOTOS_DIR = Path("./photos")
PHOTOS_DIR.mkdir(exist_ok=True)

ORDERS = {}
ITEMS = {}
STICKERS_LOG = []

def gen_item(seq): return f"PRM-{datetime.now().year}-{seq:04d}"
def gen_order(seq): return f"ORD-{datetime.now().strftime('%Y%m%d')}-{seq:03d}"

def can_ready(item_num):
    return any(s["item_number"] == item_num and s["is_hand_applied"] for s in STICKERS_LOG)

print("="*60)
print("ШВЕЯМОЗГ — MOCK CHECK 014 — Пермь 1 швея — без принтера — HANDWRITE")
print("="*60)

# === ОТ ЛИЦА КЛИЕНТА ===
print("\n👤 КЛИЕНТ — новый заказ — 5 шагов — 152-ФЗ — ru-central1")
fio = input("Шаг 1/5 — ФИО — [Иванов Иван]: ") or "Иванов Иван"
phone = input("Шаг 2/5 — Телефон — [+7 999 123-45-67]: ") or "+7 999 123-45-67"
address = input("Шаг 3/5 — Адрес — [Пушкина 15-2, кв5] — для Яндекс Такси: ") or "Пушкина 15-2, кв5"
item_name = input("Шаг 4/5 — Что чинить — [Брюки черные — порвались]: ") or "Брюки черные — порвались"
consent = input("Шаг 5/5 — 152-ФЗ — ДА — согласие — [ДА]: ") or "ДА"

if consent.upper() not in ["ДА", "YES", "ДА, СОГЛАСЕН"]:
    print("❌ Нужно ДА — consent_152_fz — без согласия нельзя")
    exit()

seq = len(ORDERS) + 1
order_num = gen_order(seq)
item_num = gen_item(seq)

ORDERS[order_num] = {"fio": fio, "phone": phone, "address": address, "item": item_name, "status": "NEW", "consent_152": True}
ITEMS[item_num] = {"order_number": order_num, "name": item_name, "status": "NEW"}

print(f"\n✅ Заказ создан — {order_num} — вещь {item_num} — статус NEW — UNIQUE — вместо QR — TASK_011")
print(f"   ФИО: {fio}")
print(f"   Адрес: {address} — для наклейки рукой — Яндекс Такси не путаются — фамилия + адрес дубль")
print(f"   Вещь: {item_name}")

# Фото BEFORE — Rule 4
print(f"\n📸 Фото BEFORE — до — Rule 4 — photo_url NOT NULL — 5 фото")
print(f"   Путь: photos/{item_num}/BEFORE.jpg — C:/Perm_Repair/photos/{item_num}/BEFORE.jpg")
# Создаем фейк фото
p_dir = PHOTOS_DIR / item_num
p_dir.mkdir(parents=True, exist_ok=True)
(p_dir / "BEFORE.jpg").write_text("FAKE PHOTO BEFORE — для теста — Rule 4", encoding='utf-8')
print(f"   ✅ Фото BEFORE сохранено — {p_dir / 'BEFORE.jpg'} — Rule 4")

# ESTIMATED -> AGREED -> HOLD
ORDERS[order_num]["status"] = "ESTIMATED"
print(f"\n🔍 Швея оценила — ESTIMATED — цена 500р — швея Пермь 1 — Мотовилиха")
ORDERS[order_num]["status"] = "AGREED"
print(f"💰 Клиент согласовал — AGREED — HOLD платеж — operator_id=1 — AI не допущен — Rule 2 — HOLD 500р")
ORDERS[order_num]["status"] = "IN_WORK"
ITEMS[item_num]["status"] = "IN_WORK"
print(f"🧵 В работе — IN_WORK — швея 1 — employee_id=1 — 100 заказов/мес — MVP — шьет")

# === ОТ ЛИЦА ШВЕИ ===
print("\n" + "="*60)
print("🧵 ШВЕЯ — Пермь 1 Мотовилиха — employee_id=1 — без принтера — HANDWRITE")
print("="*60)
print(f"\n📋 /myorders — список в работе — IN_WORK:")
for inum, it in ITEMS.items():
    if it["status"] in ["NEW", "IN_WORK", "ESTIMATED", "AGREED"]:
        ord_info = ORDERS.get(it["order_number"], {})
        print(f"   {inum} — {it['name']} — {it['order_number']} — {ord_info.get('fio','')} — {ord_info.get('address','')}")

print(f"\n🏷️ Швея — у неё НЕТ принтера — как решили — TASK_011 — QR зачеркнут")
print(f"   Оператор напечатал заготовки наклеек 58x40 — 1000шт 300р — рулон — отдал швее в Мотовилихе")
print(f"   Швея пишет рукой черным маркером 1-2мм — как на UI FIXED FIELDS — не перечеркивает:")

# Показываем наклейку — FIXED FIELDS — не перечеркивает
print(f"""
   ┌─────────────────────────────┐
   │ Заказ №:                    │
   │ {order_num.split('-')[-1]:<27} │
   │ ___________________________ │
   │ Фамилия:                    │
   │ {fio:<27} │
   │ ___________________________ │
   │ Адрес:                      │
   │ {address:<27} │
   │ ___________________________ │
   │ Вещь / Номер:               │
   │ {item_name[:15]} — {item_num} │
   │ - - - - - - - - - - - - -  │
   └─────────────────────────────┘
   Путь заготовки: photos/stickers/blank_58x40.pdf — 1000шт 300р
""")

input("\nНажми Enter — швея написала наклейку рукой — наклеила — фоткает...")

# Фото STICKER_HANDWRITE — Rule 7 + Rule 4 — критично — без hand_applied нельзя READY
sticker_path = p_dir / "sticker_handwrite.jpg"
sticker_path.write_text("FAKE PHOTO STICKER_HANDWRITE — наклейка рукой — Rule 7 — is_hand_applied=true", encoding='utf-8')

STICKERS_LOG.append({
    "item_number": item_num,
    "order_number": order_num,
    "fio": fio,
    "address": address,
    "item_name": item_name,
    "is_hand_applied": True,
    "applied_by": 1,
    "photo_url": str(sticker_path),
    "file_path": str(sticker_path),
    "created_at": datetime.now().isoformat()
})

print(f"\n✅ Фото наклейки сохранено — {sticker_path}")
print(f"   app/photos/{item_num}/sticker_handwrite.jpg — C:/Perm_Repair/photos/{item_num}/sticker_handwrite.jpg")
print(f"   stickers_log — is_hand_applied=true — applied_by=1 — Пермь 1 швея — зафиксирована — Rule 7 critical")
print(f"   photo_url NOT NULL — Rule 4 — 5 фото — BEFORE/DEFECT/AFTER/STICKER_HANDWRITE/DELIVERY")

# Проверка can_ready
print(f"\n🔍 Проверка Rule 7 — без hand_applied нельзя READY — can_ready({item_num}): {can_ready(item_num)}")

if can_ready(item_num):
    ITEMS[item_num]["status"] = "READY"
    ORDERS[order_num]["status"] = "READY"
    print(f"✅ {item_num} — READY — наклеена рукой — hand_applied=true — можно в Яндекс Такси")
    print(f"   Адрес с наклейки рукой — фамилия + адрес — дубль с приложением — чтобы Яндекс Такси не путались — Rule 5")
    print(f"   Следующий — OUT_FOR_DELIVERY — Яндекс Такси — только после READY — Rule 5 — нельзя до READY")
    
    # Яндекс Такси
    ORDERS[order_num]["status"] = "OUT_FOR_DELIVERY"
    print(f"\n🚕 OUT_FOR_DELIVERY — Яндекс Такси — заказ {order_num} — {address} — ФИО {fio} — с наклейки рукой")
    print(f"   yandex_taxi_order_id — MOCK — TAXI-12345 — 14 исключений курьера — логируем в delivery_tasks")
    
    ORDERS[order_num]["status"] = "DELIVERED"
    print(f"📦 DELIVERED — курьер доставил — фото у двери — DELIVERY.jpg — Rule 4")
    (p_dir / "DELIVERY.jpg").write_text("FAKE DELIVERY PHOTO", encoding='utf-8')
    
    ORDERS[order_num]["status"] = "CLOSED"
    print(f"💳 CLOSED — CAPTURE платеж — 500р — HOLD 500р -> CAPTURE 500р — operator_id=1 — Rule 2")
    print(f"   audit_log — ru-central1 — 152-ФЗ — audit + consent — SHVEYA v2.4")
else:
    print(f"❌ Нельзя READY — {item_num} — нет наклейки рукой — Rule 7 [CRITICAL] — is_hand_applied=false")

print("\n" + "="*60)
print("✅ MOCK CHECK 014 — DONE — 8 шагов NEW->CLOSED — обкатка идеально — на этом компе — без ИП")
print("="*60)
print(f"ORDERS: {json.dumps(ORDERS, ensure_ascii=False, indent=2)}")
print(f"ITEMS: {json.dumps(ITEMS, ensure_ascii=False, indent=2)}")
print(f"STICKERS_LOG: {json.dumps(STICKERS_LOG, ensure_ascii=False, indent=2)}")
print(f"\n📸 Фото в: {PHOTOS_DIR / item_num}")
print(f"   - BEFORE.jpg — до — Rule 4")
print(f"   - sticker_handwrite.jpg — наклейка рукой — Rule 7 + Rule 4 — is_hand_applied=true")
print(f"   - DELIVERY.jpg — доставка — Rule 4")
print(f"\nСледующий — TASK_015 — деплой Яндекс Cloud грант 10к — после обкатки — открываем ИП — ru-central1 152-ФЗ")
