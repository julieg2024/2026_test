-- raw_orders: Load raw order data from source system
-- Source: E-commerce platform / transactional DB
-- Lineage: source.ecommerce.orders -> raw.raw_orders

CREATE TABLE IF NOT EXISTS raw.raw_orders (
    order_id        INT PRIMARY KEY,
    customer_id     INT,
    order_date      DATE,
    status          VARCHAR(50),
    amount          DECIMAL(10, 2),
    payment_method  VARCHAR(50)
);

INSERT INTO raw.raw_orders (order_id, customer_id, order_date, status, amount, payment_method)
VALUES
    (101, 1, '2024-06-01', 'completed',  150.00, 'credit_card'),
    (102, 1, '2024-07-15', 'completed',   75.50, 'paypal'),
    (103, 2, '2024-06-20', 'completed',  200.00, 'credit_card'),
    (104, 3, '2024-08-01', 'returned',    50.00, 'debit_card'),
    (105, 3, '2024-08-15', 'completed',  300.00, 'credit_card'),
    (106, 4, '2024-09-10', 'completed',  125.75, 'paypal'),
    (107, 5, '2024-10-01', 'pending',     89.99, 'credit_card'),
    (108, 1, '2024-10-05', 'completed',  175.00, 'debit_card'),
    (109, 2, '2024-10-10', 'completed',   60.00, 'paypal'),
    (110, 4, '2024-10-15', 'completed',  220.50, 'credit_card');
