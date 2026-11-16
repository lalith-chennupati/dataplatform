-- Spark SQL (Data Processing Engine). pipeline.py substitutes ${env} before running.
CREATE OR REPLACE TEMPORARY VIEW latest AS
SELECT *, coalesce(amount > 0 AND order_date <= current_date() AND status IN ('O', 'F', 'P'), false) AS valid
FROM (SELECT *, row_number() OVER (PARTITION BY order_id ORDER BY _ingested_at DESC) rn FROM ${env}_raw.orders_events) WHERE rn = 1;

INSERT OVERWRITE ${env}_curated.orders_quarantine
SELECT order_id, customer_id, amount, order_date, status, _ingested_at,
       CASE WHEN amount IS NULL OR order_date IS NULL OR status IS NULL THEN 'missing value'
            WHEN amount <= 0 THEN 'non-positive amount' WHEN order_date > current_date() THEN 'future date' ELSE 'bad status' END
FROM latest WHERE NOT valid;

MERGE INTO ${env}_curated.orders_clean t
USING (SELECT order_id, customer_id, amount, order_date, status, _ingested_at FROM latest WHERE valid) s
ON t.order_id = s.order_id
WHEN MATCHED AND s._ingested_at > t._ingested_at THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
