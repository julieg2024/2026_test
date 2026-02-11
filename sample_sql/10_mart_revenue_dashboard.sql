-- Mart: final revenue dashboard combining customer and product data
INSERT INTO mart.revenue_dashboard
SELECT
    co.customer_id,
    co.first_name,
    co.last_name,
    co.total_orders,
    co.lifetime_value,
    ps.product_category,
    ps.total_revenue        AS category_revenue,
    ps.total_units_sold     AS category_units_sold,
    (ps.total_revenue / NULLIF(
        (SELECT SUM(total_revenue) FROM mart.product_sales), 0
    )) * 100                AS revenue_share_pct
FROM mart.customer_orders co
CROSS JOIN (
    SELECT
        product_category,
        SUM(total_revenue)      AS total_revenue,
        SUM(total_units_sold)   AS total_units_sold
    FROM mart.product_sales
    GROUP BY product_category
) ps
WHERE co.total_orders > 0;
