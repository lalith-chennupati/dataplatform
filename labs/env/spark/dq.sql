SELECT 'silver has no duplicate order_id' AS check, coalesce(count(*) = count(DISTINCT order_id), false) AS ok FROM curated.orders_clean
UNION ALL SELECT 'silver amounts positive', coalesce(min(amount) > 0, false) FROM curated.orders_clean
UNION ALL SELECT 'gold reconciles to silver', coalesce(abs((SELECT sum(revenue) FROM consumption.daily_revenue) - (SELECT sum(amount) FROM curated.orders_clean)) < 1, false)
UNION ALL SELECT 'quarantine below 1%', coalesce((SELECT count(*) FROM curated.orders_quarantine) < 0.01 * (SELECT count(*) FROM curated.orders_clean), false);
