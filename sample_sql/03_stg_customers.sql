-- stg_customers: Cleaned and standardized customer data
-- Lineage: raw.raw_customers -> staging.stg_customers

CREATE TABLE staging.stg_customers AS
SELECT
    customer_id,
    LOWER(TRIM(first_name))             AS first_name,
    LOWER(TRIM(last_name))              AS last_name,
    LOWER(TRIM(email))                  AS email,
    CONCAT(TRIM(first_name), ' ', TRIM(last_name)) AS full_name,
    created_at                          AS customer_since,
    updated_at                          AS last_updated
FROM raw.raw_customers
WHERE customer_id IS NOT NULL
  AND email IS NOT NULL;
