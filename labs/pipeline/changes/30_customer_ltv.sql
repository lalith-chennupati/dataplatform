INSERT OVERWRITE ${env}_consumption.customer_ltv
SELECT customer_id, count(*), round(sum(amount), 2), min(order_date), max(order_date) FROM ${env}_curated.orders_clean GROUP BY customer_id;
