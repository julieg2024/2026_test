-- stg_orders: Cleaned and standardized order data
-- Lineage: raw.raw_orders -> staging.stg_orders

CREATE TABLE staging.stg_orders AS
SELECT
    order_id,
    customer_id,
    order_date,
    LOWER(TRIM(status))             AS order_status,
    amount                          AS order_amount,
    LOWER(TRIM(payment_method))     AS payment_method,
    CASE
        WHEN status = 'completed' THEN amount
        ELSE 0
    END                             AS revenue
FROM raw.raw_orders
WHERE order_id IS NOT NULL;
