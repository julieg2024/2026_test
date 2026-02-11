-- int_customer_orders: Intermediate table joining customers with their orders
-- Lineage: staging.stg_customers + staging.stg_orders -> intermediate.int_customer_orders

CREATE TABLE intermediate.int_customer_orders AS
SELECT
    c.customer_id,
    c.full_name,
    c.email,
    c.customer_since,
    o.order_id,
    o.order_date,
    o.order_status,
    o.order_amount,
    o.payment_method,
    o.revenue,
    ROW_NUMBER() OVER (PARTITION BY c.customer_id ORDER BY o.order_date)        AS order_sequence,
    FIRST_VALUE(o.order_date) OVER (PARTITION BY c.customer_id ORDER BY o.order_date) AS first_order_date,
    LAST_VALUE(o.order_date) OVER (
        PARTITION BY c.customer_id
        ORDER BY o.order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    )                                                                           AS most_recent_order_date
FROM staging.stg_customers c
LEFT JOIN staging.stg_orders o
    ON c.customer_id = o.customer_id;
