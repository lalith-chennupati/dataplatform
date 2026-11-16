INSERT OVERWRITE ${env}_consumption.daily_revenue
SELECT order_date, status, count(*), round(sum(amount), 2) FROM ${env}_curated.orders_clean GROUP BY order_date, status;
