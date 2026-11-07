-- ============================================================
-- TASK_004 — 003_constraints_check.sql — проверка всех RULE
-- Запускать после 001 и 002 на b2.medium
-- ============================================================

\echo '=== CHECK 1: leg_number IN (1,2) ==='
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='order_legs_leg_number_check') THEN
    RAISE NOTICE 'FAIL: CHECK leg_number missing';
  ELSE RAISE NOTICE 'OK: CHECK leg_number IN (1,2)';
  END IF;
END $$;

\echo '=== CHECK 2: UNIQUE(order_id, leg_number) ==='
SELECT conname, contype FROM pg_constraint WHERE conname='uq_order_leg';

\echo '=== CHECK 3: partial unique is_current WHERE is_current ==='
SELECT indexname, indexdef FROM pg_indexes WHERE indexname IN ('ux_client_addresses_current','ux_shveya_points_current','ux_price_versions_current','ux_garment_meas_current');

\echo '=== CHECK 4: RULE v1 не удаляется ==='
SELECT tgname FROM pg_trigger WHERE tgname='trg_no_delete_v1';
-- тест: должен упасть
-- DELETE FROM price_versions WHERE version_code='v1'; -- expect ERROR

\echo '=== CHECK 5: RULE immutable transfer_history ==='
SELECT tgname FROM pg_trigger WHERE tgname IN ('trg_immutable_update','trg_immutable_delete');

\echo '=== CHECK 6: idempotency_key 3 UNIQUE ==='
SELECT indexname, indexdef FROM pg_indexes WHERE indexname IN ('ux_orders_idempotency','ux_payments_idempotency','ux_event_log_idempotency');

\echo '=== CHECK 7: pgcrypto ==='
SELECT * FROM pg_extension WHERE extname='pgcrypto';

\echo '=== CHECK 8: ENUM 10 штук ==='
SELECT COUNT(*) AS enum_count FROM pg_type WHERE typname LIKE '%_enum';
SELECT typname, enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid=pg_type.oid WHERE typname LIKE '%_enum' ORDER BY typname;

\echo '=== CHECK 9: триграм-индекс ==='
SELECT indexname, indexdef FROM pg_indexes WHERE indexname='gin_clients_name_trgm';

\echo '=== CHECK 10: GENERATED total_price ==='
SELECT column_name, is_generated, generation_expression FROM information_schema.columns WHERE table_name='order_services' AND column_name='total_price';

\echo '=== CHECK 11: 20 таблиц ==='
SELECT COUNT(*) AS tables_count FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';

\echo '=== CHECK 12: сиды ==='
SELECT 'measurements' AS tbl, COUNT(*) FROM measurements
UNION ALL SELECT 'garment_types', COUNT(*) FROM garment_types
UNION ALL SELECT 'zones', COUNT(*) FROM zones
UNION ALL SELECT 'shveya_points', COUNT(*) FROM shveya_points
UNION ALL SELECT 'state_transitions', COUNT(*) FROM state_transitions
UNION ALL SELECT 'courier_exceptions', COUNT(*) FROM courier_exceptions;

\echo 'ALL RULES CHECKED';
