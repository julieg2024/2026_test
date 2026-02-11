-- Raw products table: product catalog
CREATE TABLE raw.products (
    id              INTEGER PRIMARY KEY,
    name            VARCHAR(200),
    category        VARCHAR(100),
    subcategory     VARCHAR(100),
    price           DECIMAL(10, 2),
    cost            DECIMAL(10, 2),
    is_available    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP
);
