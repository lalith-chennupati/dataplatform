-- Trino SQL data-quality gate. One row per check: (check, ok). Thresholds come from environments.yaml.
SELECT 'silver has at least ${min_rows} rows', count(*) >= ${min_rows} FROM iceberg.${env}_curated.orders_clean
UNION ALL SELECT 'silver has no duplicate order_id', coalesce(count(*) = count(DISTINCT order_id), false) FROM iceberg.${env}_curated.orders_clean
UNION ALL SELECT 'silver amounts positive', coalesce(min(amount) > 0, false) FROM iceberg.${env}_curated.orders_clean
UNION ALL SELECT 'gold reconciles to silver', coalesce(abs((SELECT sum(revenue) FROM iceberg.${env}_consumption.daily_revenue) - (SELECT sum(amount) FROM iceberg.${env}_curated.orders_clean)) < 1, false)
UNION ALL SELECT 'quarantine <= ${max_quarantine_pct}% of silver', coalesce((SELECT count(*) FROM iceberg.${env}_curated.orders_quarantine) <= ${max_quarantine_pct} / 100.0 * (SELECT count(*) FROM iceberg.${env}_curated.orders_clean), false)
