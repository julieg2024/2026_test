-- Mart: product-level sales metrics
CREATE TABLE mart.product_sales AS
SELECT
    oi.product_id,
    oi.product_name,
    oi.product_category,
    COUNT(DISTINCT oi.order_id)     AS orders_containing_product,
    SUM(oi.quantity)                AS total_units_sold,
    SUM(oi.line_total)             AS total_revenue,
    AVG(oi.unit_price)             AS avg_selling_price,
    AVG(oi.discount_pct)           AS avg_discount_pct,
    MIN(so.order_date)             AS first_sold_date,
    MAX(so.order_date)             AS last_sold_date
FROM staging.stg_order_items oi
JOIN staging.stg_orders so
    ON oi.order_id = so.order_id
GROUP BY
    oi.product_id,
    oi.product_name,
    oi.product_category;
