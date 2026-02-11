-- raw_customers: Load raw customer data from source system
-- Source: ERP system / CSV import
-- Lineage: source.erp.customers -> raw.raw_customers

CREATE TABLE IF NOT EXISTS raw.raw_customers (
    customer_id     INT PRIMARY KEY,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(255),
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);

INSERT INTO raw.raw_customers (customer_id, first_name, last_name, email, created_at, updated_at)
VALUES
    (1, 'Alice',   'Johnson',  'alice.johnson@example.com',  '2024-01-15 10:00:00', '2024-06-01 08:30:00'),
    (2, 'Bob',     'Smith',    'bob.smith@example.com',      '2024-02-20 14:30:00', '2024-07-10 09:15:00'),
    (3, 'Charlie', 'Williams', 'charlie.w@example.com',      '2024-03-05 09:45:00', '2024-08-22 11:00:00'),
    (4, 'Diana',   'Brown',    'diana.brown@example.com',    '2024-04-12 16:00:00', '2024-09-15 13:45:00'),
    (5, 'Eve',     'Davis',    'eve.davis@example.com',      '2024-05-28 11:20:00', '2024-10-03 07:50:00');
