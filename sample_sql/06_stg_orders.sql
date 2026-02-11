-- Staging orders: enriched with customer info
CREATE TABLE staging.stg_orders AS
SELECT
    o.id            AS order_id,
    o.customer_id,
    c.first_name    AS customer_first_name,
    c.last_name     AS customer_last_name,
    c.email         AS customer_email,
    o.order_date,
    o.total_amount,
    o.status,
    o.created_at    AS order_created_at
FROM raw.orders o
JOIN raw.customers c
    ON o.customer_id = c.id
WHERE o.status != 'cancelled';
