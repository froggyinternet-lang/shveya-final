# Рабочий контракт реализации

Цель: одна FastAPI служба + PostgreSQL и React SPA из официального MIT Full Stack FastAPI Template. Исходный шаблон скопирован как база. Не переносить автомобильную модель erp-lite.

Операционный поток: клиентское сообщение с фото/текстом/голосом и адресом → выбор ближайшей активной швеи → её оценка → наценка минимум 30% (конфигурация по швее/заказу, права owner/operator) → показ цены ремонта и обоих плеч доставки → клиент подтверждает и оплачивает **одним платежом общую фиксированную сумму** → забор → ремонт → фото результата → клиент выбирает время и подтверждает обратную доставку → заказ перевозки без второй оплаты. Разница между предварительной и фактической стоимостью обратного плеча относится на CM платформы. Первые 30–50 заказов режим partner, без фактического вызова Яндекса. Адрес/геолокация запрашиваются явно; IP мессенджера недоступен.

Внутренние статусы: Order NEW, ESTIMATING, QUOTED, CONFIRMED, PICKUP, IN_WORK, QC, READY, DELIVERED, CANCELLED, DISPUTE. Garment RECEIVED, INSPECTED, IN_WORK, QC, READY_FOR_RETURN, UNREPAIRABLE. Переходы валидируются backend; события с idempotency_key UNIQUE. Фото относятся к вещи. DeliveryLeg только 1/2. Деньги Decimal, без float.

API-контракт frontend (prefix /api):
- GET /me; POST /auth/login; роли owner, operator, master, courier, customer.
- GET /admin/overview, /admin/orders, /admin/orders/{id}, /admin/masters, /admin/finance; POST /admin/masters; POST /admin/orders/{id}/assign; POST /admin/orders/{id}/quote; POST /admin/orders/{id}/dispatch-pickup.
- GET /master/jobs; POST /master/jobs/{garment_id}/accept, /ready, /problem; POST /master/jobs/{garment_id}/estimate; POST /garments/{id}/photos.
- GET /courier/legs; POST /courier/legs/{id}/pickup, /deliver.
- GET /app/orders; POST /app/orders; POST /app/orders/{id}/confirm-quote, /confirm-return.
- POST /webhooks/telegram, /webhooks/vk, /webhooks/max, /webhooks/yandex, /webhooks/yookassa.

Frontend: hash routing inside canonical /admin; landing shows owner KPIs and Vlad queue. Ru primary, es optional. /app, /master, /courier mobile pages. All calls use credentials and handle loading/error/empty. Future tabs marketing/accounting can be registered without new app shell.

Integrations module interface: standalone classes with async methods and HTTP requests, no DB mutations. Backend routes validate webhook secret then call adapter; external calls get request_id/idempotency key. No calls to live external systems in tests.

Credentials: all integrations optional until configured. Never hardcode secrets. `.env.example` must include needed bot/API credentials; prior three-token limit cannot support VK, MAX and Yandex, so current user request supersedes that limit.

User-facing claim: development-ready code with verified tests; production operation requires merchant accounts/tokens and a live end-to-end trial in Perm. Never label a simulated tariff or dispatch as live.
