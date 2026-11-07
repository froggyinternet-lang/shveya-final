# Document 2: Анализ 5 бизнес-моделей для сервиса ремонта одежды в РФ
## Дата: 3 ноября 2026

### 1. Бенчмарки российских агрегаторов бытовых услуг

#### Профи.ру
- Модель монетизации: платный отклик исполнителя за контакт. С 21 января 2026 тариф "Комиссия" отменен почти для всех категорий, комиссии с заказа нет[^1].
- Ответственность: площадка не является стороной сделки, договор между заказчиком и мастером напрямую. Гарантия ограничена возвратом стоимости отклика.
- Для ремонта одежды: заказчик публикует задачу, мастер покупает отклик, нет гарантии заказа — "Оплата отклика не гарантирует заказ"[^1].

#### YouDo.com
- История: перезапущен как сервис бытовых услуг 3 апреля 2012[^2], 16 категорий включая ремонт[^2].
- Монетизация: пакеты откликов от 50 ₽, с заказчика 11% + 35 ₽[^1]. Ранее комиссия 10%, затем 4%, с 2016 платные предложения[^2].
- Верификация: обязательное заполнение личной информации, тест на знание правил, проверка документов через нейросети[^2], значок "Проверенный".
- Масштаб: 7 млн пользователей, ~2 млн исполнителей, 6000 заданий в день (сентябрь 2019)[^2], оборот 8.7 млрд руб в 2018[^2].

#### Авито Услуги
- Аудитория: больше 60 млн пользователей в месяц[^1].
- Модель: классифайд — объявление описывает услугу и мастера, клиент пишет напрямую[^1]. Оплата за размещение или за контакты (звонки/сообщения), единой цены нет.
- Рост категории: интерес к частным портным +110% за 2 года, к ателье +116% (данные Авито 2023)[^1].
- Региональный рост: Хабаровск +243%, Иркутск +219%, Красноярск +163%[^1].

#### Мобильные ателье / выездные портные
- Не агрегатор, а сервисная модель. Критерий "Заказ по меркам" — мастер ведет клиента от мерок до примерки без ограничений формата[^1].
- Ограничение: только своя аудитория, конверсия сторис 2-4 заявки на 50-60 охватов, 1.5-2 часа в день на контент[^1].

### 2. Unit economics ремонта и логистики

#### Себестоимость ателье
- Средний чек ремонта: 
  - Базовый рынок: 300-400 руб за заказ[^3]
  - Средний ремонт: 500-1800 руб в зависимости от сложности[^4]
  - Срочный ремонт: 800-1200 руб за элемент[^5]
- Структура цены: 45% стоимости — труд портного[^3]; материалы 25%, оплата труда+аренда 40-45%, маржинальность 30-35%[^6].
- Оплата труда: сдельная 30-40% от заказа[^7] или 25-40%[^8][^9].
- Объем: хорошее ателье 20-25 заказов на пошив и 200-250 на ремонт в месяц[^10][^11]; при графике 10-20 — 15 заказов по 200-500 руб + 5 по 1500+ руб в день[^10][^11].
- Срочность: наценка 15-50% за срочность[^9].

#### Курьерская логистика
- Яндекс Доставка:
  - От 200 руб за заказ, +10-15% в зависимости от трафика и срочности[^12]
  - Тариф "Курьер" пеший/вело до 10 кг (15 кг мужчины, 10 кг женщины)[^13], пеший до 10 кг[^14]
  - Бизнес-модель пункт-выдача от 120 ₽, Москва-СПб от 185 ₽[^15][^16]
  - Страховка до 500 000 руб на все заказы, покрывает убытки по вине сервиса[^17]
- Для модели "забор-возврат" нужно 2 плеча логистики = 400-600 руб себестоимость в Москве, 300-400 в Перми.
- Альтернатива: Gophr (партнер The Seam в Лондоне) для high-value items, стоимость покрывает клиент[^18].

### 3. Международные бенчмарки

#### Sojo (UK, "Deliveroo for repairs")
- Модель: D2C + B2B[^19], велосипедные курьеры в зонах 1-2 Лондона, сбор-возврат 3-5 дней[^20].
- Монетизация: 30% комиссия с заказов для покрытия маркетинга, платежей, инфраструктуры, гарантий[^20][^19] + £3.99 delivery fee за забор и возврат[^21].
- Сеть: 10 seamsters на старте[^22], цены устанавливают сами мастера, Sojo берет 30%[^22][^21].
- B2B pivot: партнерства с Marks & Spencer, Reiss, Arket, Selfridges, Ganni[^23], ремонт от £5, 7-10 дней turnaround[^24], для Selfridges repair 12% circular revenue 2025, +10% YoY[^25].

#### The Seam (UK marketplace)
- Модель: маркетплейс, Maker ставит цену = сколько получает, клиент платит +20% service fee в пользу The Seam[^18].
- Покрытие fee: technology, marketing, customer service, Maker support[^18].
- Логика: независимые Maker, свободны принимать/отклонять заказы[^18], ответственность за вещи на Maker — liable for full cost if lost[^18], обязательная страховка доставки Royal Mail Special Delivery до £2500[^18].
- Rush fee: до 40% за ≤3 дня[^18].

#### Save Your Wardrobe (SYW, UK/EU SaaS)
- Pivot: из consumer closet app в B2B2C platform, победа LVMH Innovation Award 2023[^26].
- Модель: Circular-Platform-as-a-Service, white-label backend для ритейлеров Zalando, Harrods[^26][^27], B2B white-label сокращает costs до 60% vs in-house build, снижает возвраты на 12% (pilot 2025)[^28].
- Монетизация SaaS: €1500/мес basic API до €12 000/мес full white-label (примеры цен 2025), annual -15%[^28].
- Поток данных: лицензия отчетов €10k-€200k annual, выручка €3.6M (25% margin) в FY2025[^28][^29].
- Экономика ремонта для потребителя: средний ремонт 37% от стоимости вещи, экономия ~£113 vs замена[^30][^31], 63% дешевле retail value включая доставку и наценку бренда[^32], стоимость ремонта £15-£60[^33].
- Партнерства: приобретение Les Raccommodeurs (FR B2B) в сент 2025 для входа в континентальную Европу[^34], H&M France[^34][^35], Klarna Care & Repair[^36].

### 4. Пять моделей A-E для РФ

#### Модель A: Легкий маркетплейс (The Seam клон)
- Суть: P2P доска, мастер выставляет прайс, платформа +20% сверху как The Seam[^18].
- Ответственность: агентская схема, не сторона сделки, как Profi.ru/YouDo. Maker liable за потерю.
- Плюсы: низкая операционка, быстрый MVP, нет логистики.
- Минусы: нет контроля качества, как Avito — "порядок мерок, примерок и предоплаты мастер выстраивает сам"[^1], высокий churn из-за ухода в оффлайн.
- Комиссия: 20% service fee. При среднем чеке 800 руб → 160 руб выручка платформы.

#### Модель B: Managed marketplace с логистикой (Sojo клон)
- Суть: забор-ремонт-возврат велокурьером, 30% комиссия + delivery fee как Sojo[^20][^19].
- Ответственность: платформа как агент-экспедитор, страховка 500k от Яндекс Доставки[^17], SLA 5 дней.
- Unit: Чек 1200 руб (средний ремонт 800 + наценка за выезд), комиссия 30% = 360 руб + доставка 399 руб (2 плеча по 200) = 759 руб выручка, себестоимость логистики 400 + поддержка 100 + эквайринг 2.9% = ~570, маржа ~189 руб (25%).
- Плюсы: контроль опыта, высокий LTV.
- Минусы: операционно тяжело, нужен флот/партнер.

#### Модель C: Ателье-хаб (dark atelier)
- Суть: собственный цех + курьеры, как хорошее ателье с 200-250 ремонтами/мес[^10][^11], вертикальная интеграция.
- Экономика: чек 800 руб, себестоимость 45% труд + 25% материалы = 70%, аренда+маркетинг 15%, маржа 15% без логистики. С логистикой +400 руб к чеку → чек 1200, маржа выше.
- Ответственность: полная, как исполнитель, гарантия качества.
- Плюсы: контроль качества, маржа на труде.
- Минусы: CAPEX, найм швей (10-15k руб оклад или 30-40% сдельно[^7]), масштаб только через франшизу.

#### Модель D: B2B2C для брендов (Save Your Wardrobe клон)
- Суть: SaaS для ритейлеров — white-label ремонт, как SYW для Zalando/Harrods[^26][^27]. Бренд платит фикс €1500-12000/мес[^28] + per order.
- Пример: M&S fixed by Sojo — ремонт от £5, 7-10 дней[^24], бренд subsidizes доставку.
- Для РФ: партнерство с Lamoda, 12storeez, 2Mood, Sela. Предложение: снизить возвраты на 12%[^28] и продлить жизнь вещи (ESG).
- Монетизация: SaaS + take rate 15-20% с ремонта, бренд покрывает логистику.
- Плюсы: высокий чек B2B, низкая CAC, тренд ESG.
- Минусы: длинный цикл продаж, нужна интеграция.

#### Модель E: Гибрид (рекомендуемая)
- Суть: A + B + D. Старт как легкий маркетплейс (Модель A) с верификацией как YouDo[^2], опция "ремонт с забором" через Яндекс Доставку (Модель B), и пилот B2B2C с 1-2 брендами (Модель D).
- Потоки: 
  1) Self-service (70% заказов): клиент везет сам → комиссия 20%
  2) Managed (25%): забор-возврат → комиссия 30% + delivery
  3) B2B (5% старт): бренды → SaaS + 20%
- Ответственность: агентский договор (платформа — агент принципала-ателье, чек с признаком агента по 54-ФЗ[^37]), страховка Яндекс 500k[^17].

### 5. Рекомендация по запуску
- Москва: старт с Моделью E, фокус на B2C managed (чек выше, плотность курьеров).
- Пермь: Модель A + C (dark atelier партнера), логистика дороже из-за расстояний, лучше self-service.

[^1]: Площадка для мастеров по пошиву одежды на заказ: где искать клиентов и на чём портные теряют деньги — https://vc.ru/ask/3214410-gde-nayti-klientov-dlya-poshiva-odezhdy-na-zakaz
[^2]: Youdo — https://ru.wikipedia.org/wiki/Youdo
[^3]: Эта часть работы выложена в ознакомительных целях. Если вы хотите получить работу полностью, то — https://orenburg.studservis.ru/gotovye-raboty/download/519158
[^4]: Материалы за 02.11.2026 » Ателье Анаэль - Пошив и ремонт — https://w01.anael-atele.ru/2026/11/02/
[^5]: Что выбрать: ателье пошив или самостоятельный ремонт одежды? — https://w01.anael-atele.ru/2991-vybrat-atel-poshiv-5.html
[^6]: Сам себе портной: сколько можно заработать на пошиве одежды и обуви — https://www.rbc.ru/ins/own_business/14/10/2015/561e0d819a79471bfeaf93be
[^7]: Как открыть ателье: руководство для начинающих — https://znatokfinansov.ru/biznes/biznes-atele-po-posivu-i-remontu-odezdy/
[^8]: Бизнес-план Ателье по пошиву и ремонту одежды — https://bi-plan.ru/pdf/0B_cb_4qCr3IwTVRLUHZLYy1ybkk.pdf
[^9]: Сколько будет стоить сшить платье в ателье — https://megavtogal.com/shite/skolko-budet-stoit-sshit-plate-v-atele.html
[^10]: Businessplan für individuelles Tailoring.  Verdienen ohne das Haus zu verlassen oder Nähen als Geschäftsidee — https://optolov.ru/de/the-ceiling-in-the-bathroom/biznes-plan-individualnyi-poshiv-odezhdy-zarabotok-ne-vyhodya-iz-doma-ili.html
[^11]: Open a tailoring studio from scratch.  Main stages of project implementation — https://koon.ru/en/otkryt-atele-po-poshivu-odezhdy-s-nulya-osnovnye-etapy-realizacii/
[^12]: Стоимость Яндекс Доставки в 2025 году — https://ggf360.ru/tehnika/kondensator/skolko-stoit-yandeks-dostavka
[^13]: Тарифы курьера в Яндекс Про: Курьер, Экспресс, авто — https://kyrieros.ru/blog/tarify-kurera-yandeks-pro/
[^14]: О быстрой доставке для вашего бизнеса — Яндекс Доставка — https://dostavka.yandex.ru/about/
[^15]: Дешево и надежно: как выбрать службу доставки для личных посылок — Сервисы на vc.ru — http://vc.ru/services/3017876-kak-vybrat-sluzhbu-dostavki-dlya-lichnykh-posylok
[^16]: Как работает "Яндекс Доставка": все тонкости и нюансы — https://fb.ru/article/516209/2023-kak-rabotaet-yandeks-dostavka-vse-tonkosti-i-nyuansyi?comment_id=511308
[^17]: Доставка для малого бизнеса — Яндекс Доставка — https://dostavka.yandex.ru/business/small/
[^18]: COS test | The Seam — https://www.theseam.uk/copy-of-maker-terms
[^19]: Sojo - the UK's first clothing repair app connects users to local seamsters via bike — https://knowledge-hub.circle-economy.com/article/18590
[^20]: Sojo - The 'Deliveroo' of clothing alterations & repair | Circular X — https://www.circularx.eu/en/cases/64/sojo-the-deliveroo-of-clothing-alterations-repair
[^21]: Building a billion dollar business by fixing clothes | Sifted — https://sifted.eu/articles/sojo-raise
[^22]: Sojo: The Deliveroo of fashion repairs — https://www.voguebusinessstaging.com/companies/sojo-the-deliveroo-of-fashion-repairs
[^23]: SOJO company information, funding & investors | Dealroom.co — https://app.dealroom.co/companies/sojo
[^24]: Marks and Spencer clothing repair service needs close attention and risks unravelling if demand exceeds expectations — https://Retailtechinnovationhub.com/home/2024/7/1/marks-and-spencer-clothing-repair-service-needs-close-attention-and-risks-unravelling-if-demand-exceeds-expectations
[^25]: Clothing Repair Is Driving Circular Growth at Selfridges — And SOJO Is Helping Lead the Way – Blog — https://sojo.uk/blog/selfridges-clothing-repair-growth
[^26]: What is Sales and Marketing Strategy of Save Your Wardrobe Company? – businessmodelcanvastemplate.com — https://canvasbusinessmodel.com/blogs/marketing-strategy/save-your-wardrobe-marketing-strategy
[^27]: PESTLE Analysis of Save Your Wardrobe — https://canvasbusinessmodel.com/es/products/save-your-wardrobe-pestle-analysis
[^28]: Marketing Mix Analysis of Save Your Wardrobe — https://canvasbusinessmodel.com/es/products/save-your-wardrobe-marketing-mix
[^29]: What are the Porter's Five Forces of Save Your Wardrobe — https://canvasbusinessmodel.com/pt/products/save-your-wardrobe-porters-five-forces
[^30]: UK households could save over £370 a year by repairing instead of replacing | Klarna International — https://www.klarna.com/international/press/uk-households-could-save-over-gbp370-a-year-by-repairing-instead-of-replacing/
[^31]: Frequently Asked Questions | Save Your Wardrobe — https://www.saveyourwardrobe.com/legal/faq
[^32]: Save Your Wardrobe powers Klarna’s Care & Repair feature in the UK and France — https://www.saveyourwardrobe.com/en-gb/blog/save-your-wardrobe-powers-klarnas-care-and-repair-feature
[^33]: Repair vs Returns: Which Saves Brands More Money? — https://www.saveyourwardrobe.com/en-gb/blog/every-return-costs-more-than-you-think
[^34]: Save Your Wardrobe Expands Repair Services Through French Acquisition and Strategic Partnerships — https://eustartups.news/save-your-wardrobe-expands-repair-services-through-french-acquisition-and-strategic-partnerships/
[^35]: Save Your Wardrobe news and archive — https://fashionunited.com/tags/save-your-wardrobe
[^36]: Klarna launches Care & Repair feature in UK and France to boost apparel lifespan — https://fashionunited.uk/news/fashion/klarna-launches-care-repair-feature-in-uk-and-france-to-boost-apparel-lifespan/2026093090624?utm_source=dlvr.it&utm_medium=facebook
[^37]: Агентский договор с поставщиком — МАРШРУТ — https://partners.marshrut.me/dogovory/04-dogovor-s-otelem.html
