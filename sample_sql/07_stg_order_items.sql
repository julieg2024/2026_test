-- Staging order items: enriched with product details (as a view)
CREATE VIEW staging.stg_order_items AS
SELECT
    oi.id           AS order_item_id,
    oi.order_id,
    oi.product_id,
    p.name          AS product_name,
    p.category      AS product_category,
    oi.quantity,
    oi.unit_price,
    oi.discount_pct,
    (oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100)) AS line_total
FROM raw.order_items oi
JOIN raw.products p
    ON oi.product_id = p.id;
