-- fct_orders: Fact table for order analytics
-- Lineage: intermediate.int_customer_orders -> marts.fct_orders

CREATE TABLE marts.fct_orders AS
SELECT
    order_id,
    customer_id,
    full_name               AS customer_name,
    order_date,
    order_status,
    order_amount,
    revenue,
    payment_method,
    order_sequence,
    CASE
        WHEN order_sequence = 1 THEN 'new'
        ELSE 'returning'
    END                     AS customer_type,
    order_date - first_order_date AS days_since_first_order
FROM intermediate.int_customer_orders
WHERE order_id IS NOT NULL;
