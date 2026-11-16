CREATE TABLE IF NOT EXISTS consumption.daily_revenue (order_date DATE, status STRING, orders BIGINT, revenue DOUBLE) USING iceberg;
INSERT OVERWRITE consumption.daily_revenue
SELECT order_date, status, count(*), round(sum(amount), 2) FROM curated.orders_clean GROUP BY order_date, status;
