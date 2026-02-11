-- Mart: customer order summary using CTEs
CREATE TABLE mart.customer_orders AS
WITH customer_base AS (
    SELECT
        customer_id,
        first_name,
        last_name,
        email,
        customer_since
    FROM staging.stg_customers
),
order_summary AS (
    SELECT
        customer_id,
        COUNT(*)            AS total_orders,
        SUM(total_amount)   AS lifetime_value,
        MIN(order_date)     AS first_order_date,
        MAX(order_date)     AS last_order_date,
        AVG(total_amount)   AS avg_order_value
    FROM staging.stg_orders
    GROUP BY customer_id
)
SELECT
    cb.customer_id,
    cb.first_name,
    cb.last_name,
    cb.email,
    cb.customer_since,
    COALESCE(os.total_orders, 0)    AS total_orders,
    COALESCE(os.lifetime_value, 0)  AS lifetime_value,
    os.first_order_date,
    os.last_order_date,
    COALESCE(os.avg_order_value, 0) AS avg_order_value
FROM customer_base cb
LEFT JOIN order_summary os
    ON cb.customer_id = os.customer_id;
