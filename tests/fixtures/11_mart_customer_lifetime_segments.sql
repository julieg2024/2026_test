-- Mart: customer lifetime value segments using nested CTEs
CREATE TABLE mart.customer_lifetime_segments AS
WITH order_totals AS (
    SELECT
        customer_id,
        order_id,
        SUM(quantity * unit_price) AS order_total
    FROM staging.stg_order_items
    GROUP BY customer_id, order_id
),
customer_metrics AS (
    SELECT
        ot.customer_id,
        COUNT(DISTINCT ot.order_id)  AS num_orders,
        SUM(ot.order_total)          AS lifetime_value,
        MIN(o.order_date)            AS first_order,
        MAX(o.order_date)            AS last_order
    FROM order_totals ot
    JOIN staging.stg_orders o
        ON ot.customer_id = o.customer_id
       AND ot.order_id = o.order_id
    GROUP BY ot.customer_id
),
segmented AS (
    SELECT
        cm.customer_id,
        c.first_name,
        c.last_name,
        cm.num_orders,
        cm.lifetime_value,
        cm.first_order,
        cm.last_order,
        CASE
            WHEN cm.lifetime_value >= 1000 THEN 'platinum'
            WHEN cm.lifetime_value >= 500  THEN 'gold'
            WHEN cm.lifetime_value >= 100  THEN 'silver'
            ELSE 'bronze'
        END AS segment
    FROM customer_metrics cm
    JOIN staging.stg_customers c
        ON cm.customer_id = c.customer_id
)
SELECT
    customer_id,
    first_name,
    last_name,
    num_orders,
    lifetime_value,
    first_order,
    last_order,
    segment
FROM segmented;
