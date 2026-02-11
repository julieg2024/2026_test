-- dim_customers: Dimension table with customer summary metrics
-- Lineage: intermediate.int_customer_orders -> marts.dim_customers

CREATE TABLE marts.dim_customers AS
SELECT
    customer_id,
    full_name,
    email,
    customer_since,
    MIN(order_date)                                     AS first_order_date,
    MAX(order_date)                                     AS most_recent_order_date,
    COUNT(DISTINCT order_id)                            AS total_orders,
    SUM(revenue)                                        AS lifetime_revenue,
    AVG(revenue)                                        AS avg_order_value,
    COUNT(DISTINCT CASE WHEN order_status = 'returned' THEN order_id END) AS returned_orders,
    CASE
        WHEN COUNT(DISTINCT order_id) >= 3 THEN 'high'
        WHEN COUNT(DISTINCT order_id) = 2  THEN 'medium'
        WHEN COUNT(DISTINCT order_id) = 1  THEN 'low'
        ELSE 'none'
    END                                                 AS engagement_tier
FROM intermediate.int_customer_orders
GROUP BY customer_id, full_name, email, customer_since;
