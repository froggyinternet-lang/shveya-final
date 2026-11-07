-- ============================================================
-- TASK_004 — 002_seed.sql — сиды для b2.medium
-- ============================================================

-- measurements 6
INSERT INTO measurements (id, code, name, unit) VALUES
(1, 'LENGTH', 'Длина', 'cm'),
(2, 'WIDTH', 'Ширина', 'cm'),
(3, 'SLEEVE', 'Рукав', 'cm'),
(4, 'WAIST', 'Талия', 'cm'),
(5, 'HIPS', 'Бедра', 'cm'),
(6, 'INSEAM', 'Внутренний шов', 'cm')
ON CONFLICT (id) DO NOTHING;

-- garment_types 6
INSERT INTO garment_types (id, code, name) VALUES
(1, 'PANTS', 'Брюки'),
(2, 'JACKET', 'Куртка'),
(3, 'DRESS', 'Платье'),
(4, 'SHIRT', 'Рубашка'),
(5, 'JEANS', 'Джинсы'),
(6, 'COAT', 'Пальто')
ON CONFLICT (id) DO NOTHING;

-- zones — Мотовилиха + др районы Перми
INSERT INTO zones (id, code, name, city) VALUES
(gen_random_uuid(), 'MOTOVILIKHA', 'Мотовилиха', 'Пермь'),
(gen_random_uuid(), 'SVERDLOVSKY', 'Свердловский', 'Пермь'),
(gen_random_uuid(), 'INDUSTRIAL', 'Индустриальный', 'Пермь'),
(gen_random_uuid(), 'KIROVSKY', 'Кировский', 'Пермь'),
(gen_random_uuid(), 'ORDZHONIKIDZE', 'Орджоникидзевский', 'Пермь'),
(gen_random_uuid(), 'LENINSKY', 'Ленинский', 'Пермь')
ON CONFLICT (code) DO NOTHING;

-- Shveya Points 2 — используем зоны
DO $$
DECLARE
  z_moto UUID;
BEGIN
  SELECT id INTO z_moto FROM zones WHERE code='MOTOVILIKHA' LIMIT 1;
  INSERT INTO shveya_points (code, name, zone_id, address, status) VALUES
  ('POINT_MOTOVILIKHA_1', 'Shveya Point Мотовилиха 1', z_moto, 'ул. Уральская, 75, Пермь', 'OPEN'),
  ('POINT_CENTRAL', 'Shveya Point Центр', z_moto, 'ул. Ленина, 58, Пермь', 'OPEN')
  ON CONFLICT (code) DO NOTHING;
END $$;

-- price_versions — v1 защищенная
INSERT INTO price_versions (version_code, is_current) VALUES
('v1', false),
('v2', true)
ON CONFLICT (version_code) DO NOTHING;

-- services — пример прайса для v2
DO $$
DECLARE v2 UUID;
BEGIN
  SELECT id INTO v2 FROM price_versions WHERE version_code='v2';
  INSERT INTO services (code, name, garment_type_id, price_version_id, unit_price) VALUES
  ('HEM_PANTS', 'Подшив брюк', 1, v2, 500),
  ('ZIP_REPLACE', 'Замена молнии', 2, v2, 800),
  ('DRESS_TAKEIN', 'Ушив платья', 3, v2, 1200),
  ('SHIRT_SHORTEN', 'Укоротить рубашку', 4, v2, 400),
  ('JEANS_PATCH', 'Заплатка джинсы', 5, v2, 600),
  ('COAT_REPAIR', 'Ремонт пальто', 6, v2, 1500)
  ON CONFLICT (code, price_version_id) DO NOTHING;
END $$;

-- state_transitions 13 — 8 для ORDER + 5 для GARMENT
INSERT INTO state_transitions (id, from_status, to_status, entity) VALUES
-- ORDER 8 шагов NEW→DELIVERED
(1, 'NEW', 'ACCEPTED', 'ORDER'),
(2, 'ACCEPTED', 'PICKUP_SCHEDULED', 'ORDER'),
(3, 'PICKUP_SCHEDULED', 'PICKED_UP', 'ORDER'),
(4, 'PICKED_UP', 'IN_WORK', 'ORDER'),
(5, 'IN_WORK', 'READY', 'ORDER'),
(6, 'READY', 'OUT_FOR_DELIVERY', 'ORDER'),
(7, 'OUT_FOR_DELIVERY', 'DELIVERED', 'ORDER'),
(8, 'NEW', 'CANCELLED', 'ORDER'),
-- GARMENT 5 шагов
(9, 'RECEIVED', 'DIAGNOSIS', 'GARMENT'),
(10, 'DIAGNOSIS', 'IN_REPAIR', 'GARMENT'),
(11, 'IN_REPAIR', 'QC', 'GARMENT'),
(12, 'QC', 'READY', 'GARMENT'),
(13, 'READY', 'ISSUED', 'GARMENT')
ON CONFLICT (id) DO NOTHING;

-- courier_exceptions 14
INSERT INTO courier_exceptions (id, code, name, description, is_retryable) VALUES
(1, 'CLIENT_NO_SHOW', 'Клиент не вышел', 'Клиент не вышел на точку', true),
(2, 'ADDRESS_WRONG', 'Неверный адрес', 'Адрес не найден', false),
(3, 'CLIENT_REFUSED', 'Отказ клиента', 'Клиент отказался', false),
(4, 'DAMAGE', 'Повреждение', 'Повреждено при перевозке', false),
(5, 'LOST', 'Утеря', 'Утеряно', false),
(6, 'DELAY', 'Задержка', 'Опоздание курьера', true),
(7, 'WEATHER', 'Погода', 'Непогода', true),
(8, 'ROAD_CLOSED', 'Дорога закрыта', 'Перекрытие', true),
(9, 'VEHICLE_BREAK', 'Поломка ТС', 'Поломка', true),
(10, 'OVERLOAD', 'Перегруз', 'Перегруз курьера', true),
(11, 'WRONG_POINT', 'Не та точка', 'Доставлено не туда', true),
(12, 'DOOR_CLOSED', 'Дверь закрыта', 'Не открыли дверь', true),
(13, 'PHONE_OFF', 'Телефон выкл', 'Не дозвониться', true),
(14, 'OTHER', 'Прочее', 'Иное', true)
ON CONFLICT (id) DO NOTHING;

-- idempotency_registry сид для v1
INSERT INTO idempotency_registry (key, scope) VALUES ('seed-v1', 'system') ON CONFLICT (key) DO NOTHING;
