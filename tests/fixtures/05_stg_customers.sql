-- Staging customers: cleaned and deduplicated
CREATE TABLE staging.stg_customers AS
SELECT
    id              AS customer_id,
    TRIM(first_name) AS first_name,
    TRIM(last_name)  AS last_name,
    LOWER(TRIM(email)) AS email,
    phone,
    created_at      AS customer_since,
    is_active
FROM raw.customers
WHERE email IS NOT NULL;
