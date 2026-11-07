# ER Diagram — 20 сущностей — b2.medium

```mermaid
erDiagram
  clients ||--o{ client_addresses : has
  clients ||--o{ orders : places
  zones ||--o{ client_addresses : in
  zones ||--o{ shveya_points : contains
  zones ||--o{ couriers : zone
  zones ||--o{ orders : zone
  shveya_points ||--o{ orders : point
  shveya_points ||--o{ order_legs : from
  couriers ||--o{ order_legs : delivers
  orders ||--o{ order_legs : "1=pickup 2=delivery CHECK IN(1,2) UNIQUE(order_id,leg_number)"
  orders ||--o{ garments : contains
  garment_types ||--o{ garments : type
  garment_types ||--o{ services : priced
  garments ||--o{ garment_measurements : measured
  measurements ||--o{ garment_measurements : defines
  garment_measurements }o--|| garments : "partial UNIQUE is_current"
  price_versions ||--o{ services : version
  price_versions ||--o{ order_services : locked_version
  services ||--o{ order_services : used
  garments ||--o{ order_services : for
  orders ||--o{ order_services : "GENERATED total_price = qty*unit_price"
  orders ||--o{ payments : paid
  orders ||--o{ transfer_history : "immutable RULE"
  orders ||--o{ event_log : logged
  order_legs ||--o{ transfer_history : leg
  orders ||--o{ idempotency_registry : idem

  clients {
    uuid id PK
    text phone UNIQUE
    text full_name GIN_trgm
    enum status
    timestamptz created_at
  }
  orders {
    uuid id PK
    uuid client_id FK
    enum status NEWtoDELIVERED
    text idempotency_key UNIQUE1
    numeric total_price_locked
    timestamptz price_locked_at
  }
  order_legs {
    uuid id PK
    uuid order_id FK
    smallint leg_number CHECK_1_2
    enum status
    UNIQUE order_id_leg_number
  }
  garments {
    uuid id PK
    uuid order_id FK
    smallint garment_type_id FK
    enum status RECEIVEDtoISSUED
  }
  price_versions {
    uuid id PK
    text version_code UNIQUE v1_protected
    bool is_current partial_UNIQUE
  }
  transfer_history {
    uuid id PK
    enum transfer_type
    jsonb meta
    RULE_immutable_no_UPDATE_DELETE
  }
  event_log {
    uuid id PK
    enum event_type
    jsonb payload
    text idempotency_key UNIQUE3
  }
  payments {
    uuid id PK
    numeric amount
    text idempotency_key UNIQUE2
  }
```

## 20 таблиц список
1. clients
2. client_addresses (partial unique is_current)
3. garment_types (6)
4. measurements (6)
5. zones (Мотовилиха...)
6. shveya_points (2, partial unique is_current)
7. couriers
8. orders (idempotency UNIQUE 1/3)
9. order_legs (CHECK leg_number IN 1,2 + UNIQUE order_id,leg_number)
10. garments
11. garment_measurements (partial unique)
12. price_versions (partial unique is_current + RULE v1 не удаляется)
13. services
14. order_services (GENERATED total_price)
15. payments (idempotency UNIQUE 2/3)
16. transfer_history (immutable RULE)
17. event_log (idempotency UNIQUE 3/3)
18. state_transitions (13)
19. courier_exceptions (14)
20. idempotency_registry

## Связи ключевые
- clients → orders → garments → order_services
- order_legs 1 = забор, 2 = доставка
- price_versions v1 защищена триггером
- transfer_history только INSERT
