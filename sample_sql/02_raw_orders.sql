-- Raw orders table: transactional order data
CREATE TABLE raw.orders (
    id              INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    order_date      DATE,
    total_amount    DECIMAL(12, 2),
    status          VARCHAR(20),
    shipping_address VARCHAR(500),
    created_at      TIMESTAMP
);
