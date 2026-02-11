-- Raw customers table: source system data
CREATE TABLE raw.customers (
    id              INTEGER PRIMARY KEY,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);
