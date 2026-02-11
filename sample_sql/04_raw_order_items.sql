-- Raw order items table: line items for each order
CREATE TABLE raw.order_items (
    id              INTEGER PRIMARY KEY,
    order_id        INTEGER,
    product_id      INTEGER,
    quantity         INTEGER,
    unit_price      DECIMAL(10, 2),
    discount_pct    DECIMAL(5, 2) DEFAULT 0
);
