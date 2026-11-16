SELECT 'silver has no duplicate order_id' AS check, count(*) = count(DISTINCT order_id) AS ok FROM curated.orders_clean
UNION ALL SELECT 'silver amounts positive', min(amount) > 0 FROM curated.orders_clean
UNION ALL SELECT 'gold reconciles to silver', abs((SELECT sum(revenue) FROM consumption.daily_revenue) - (SELECT sum(amount) FROM curated.orders_clean)) < 1
UNION ALL SELECT 'quarantine below 1%', (SELECT count(*) FROM curated.orders_quarantine) < 0.01 * (SELECT count(*) FROM curated.orders_clean);
