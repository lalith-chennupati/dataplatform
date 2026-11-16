# B04 - Data prep with the Data Processing Engine

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Spark 3.5 + Iceberg) / DEMO / HW (RAPIDS on GPU nodes) | 4 h | LAK, ING, DAT | B02; `make up PROFILES="core spark"` |

The Dell Data Processing Engine is Spark-based. The SQL below is standard Spark SQL with Iceberg. On the Dell engine, submit the same SQL or PySpark as a job in its UI/API.

## Steps

### Step 1 - Pipeline layout
| Layer | Table | Rule |
|---|---|---|
| bronze | `raw.orders_events` | append-only, as landed, plus `_ingested_at` |
| silver | `curated.orders_clean` | typed, deduplicated on `order_id`, invalid rows quarantined |
| gold | `consumption.daily_revenue` | aggregate per day/status, ready for BI/ML |

### Step 2 - Land bronze data, including duplicates and bad rows
```bash
cd labs/env
bin/spark-sql -e "
CREATE NAMESPACE IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.orders_events (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status STRING, _ingested_at TIMESTAMP) USING iceberg;
INSERT INTO raw.orders_events SELECT order_id, customer_id, amount, order_date, status, current_timestamp() FROM curated.orders;
INSERT INTO raw.orders_events SELECT order_id, customer_id, amount, order_date, status, current_timestamp() FROM curated.orders LIMIT 500;
INSERT INTO raw.orders_events VALUES (-1, 1, -10.0, DATE'2099-01-01', 'X', current_timestamp());
SELECT count(*), count(DISTINCT order_id) FROM raw.orders_events;"
```
The first `bin/spark-sql` call downloads the Iceberg jars into the `ivy-cache` volume, which takes 1-2 minutes. Later calls are faster.

### Step 3 - Silver: clean, dedupe, quarantine (idempotent MERGE)
The lab ships it as `labs/env/spark/silver.sql`. The folder is mounted at `/opt/lab` in the Spark container.
```sql
CREATE TABLE IF NOT EXISTS curated.orders_clean (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status STRING, _ingested_at TIMESTAMP)
USING iceberg PARTITIONED BY (months(order_date));
CREATE TABLE IF NOT EXISTS curated.orders_quarantine (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status STRING, _ingested_at TIMESTAMP, reason STRING) USING iceberg;

CREATE OR REPLACE TEMPORARY VIEW latest AS
SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY order_id ORDER BY _ingested_at DESC) rn FROM raw.orders_events) WHERE rn = 1;

INSERT OVERWRITE curated.orders_quarantine
SELECT order_id, customer_id, amount, order_date, status, _ingested_at,
       CASE WHEN amount <= 0 THEN 'non-positive amount' WHEN order_date > current_date() THEN 'future date' ELSE 'bad status' END
FROM latest WHERE amount <= 0 OR order_date > current_date() OR status NOT IN ('O', 'F', 'P');

MERGE INTO curated.orders_clean t
USING (SELECT order_id, customer_id, amount, order_date, status, _ingested_at FROM latest
       WHERE amount > 0 AND order_date <= current_date() AND status IN ('O', 'F', 'P')) s
ON t.order_id = s.order_id
WHEN MATCHED AND s._ingested_at > t._ingested_at THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```
```bash
bin/spark-sql -f /opt/lab/silver.sql
bin/spark-sql -e "SELECT count(*) FROM curated.orders_clean; SELECT reason, count(*) FROM curated.orders_quarantine GROUP BY reason"
```

### Step 4 - Gold
`labs/env/spark/gold.sql`:
```sql
CREATE TABLE IF NOT EXISTS consumption.daily_revenue (order_date DATE, status STRING, orders BIGINT, revenue DOUBLE) USING iceberg;
INSERT OVERWRITE consumption.daily_revenue
SELECT order_date, status, count(*), round(sum(amount), 2) FROM curated.orders_clean GROUP BY order_date, status;
```
`bin/spark-sql -f /opt/lab/gold.sql`

### Step 5 - Data-quality gate
`labs/env/spark/dq.sql` returns one row per check. The pipeline fails if any check fails:
```sql
SELECT 'silver has no duplicate order_id' AS check, count(*) = count(DISTINCT order_id) AS ok FROM curated.orders_clean
UNION ALL SELECT 'silver amounts positive', min(amount) > 0 FROM curated.orders_clean
UNION ALL SELECT 'gold reconciles to silver', abs((SELECT sum(revenue) FROM consumption.daily_revenue) - (SELECT sum(amount) FROM curated.orders_clean)) < 1
UNION ALL SELECT 'quarantine below 1%', (SELECT count(*) FROM curated.orders_quarantine) < 0.01 * (SELECT count(*) FROM curated.orders_clean);
```
```bash
bin/spark-sql -f /opt/lab/dq.sql | tee ../evidence/b04-dq.txt
! grep -q false ../evidence/b04-dq.txt && echo "DQ PASSED"
```
In a real pipeline, use a DQ framework (Great Expectations, Soda, or Deequ) and publish the results next to the table.

### Step 6 - Prove idempotency
Run Steps 3-5 a second time without new data:
```bash
bin/spark-sql -e "SELECT count(*), sum(amount) FROM curated.orders_clean"   # same numbers as the first run
bin/spark-sql -e "SELECT count(*) FROM curated.orders_clean.snapshots"      # MERGE with no changes may still add a snapshot; row counts must not change
```

### Step 7 - Orchestrate
`labs/env/spark/pipeline.sh` wraps the steps:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for s in silver gold; do bin/spark-sql -f /opt/lab/$s.sql; done
bin/spark-sql -f /opt/lab/dq.sql | tee /tmp/dq.txt; ! grep -q false /tmp/dq.txt
```
Schedule it with the orchestrator your standard names:
- **Airflow:** a DAG with three `BashOperator`/`SparkSubmitOperator` tasks, silver >> gold >> dq.
- **Argo Workflows on Kubernetes:** a three-step workflow that runs the Spark image (with the Spark Operator: one `SparkApplication` per step).
Record the retries, alerting and backfill behaviour.

### Step 8 - [HW] CPU vs GPU (RAPIDS Accelerator)
On a GPU node, use the same pipeline with a bigger input (e.g. TPC-H SF100 generated with `tpch.sf100` from Trino into `raw`). Add:
```
--jars rapids-4-spark_2.12-<ver>.jar --conf spark.plugins=com.nvidia.spark.SQLPlugin --conf spark.rapids.sql.enabled=true
--conf spark.executor.resource.gpu.amount=1 --conf spark.task.resource.gpu.amount=0.25
```
Record the runtime, node-hours and the cost per run for CPU and for GPU. Use the RAPIDS qualification tool on CPU event logs first, to predict which stages benefit.

## Verify
- [ ] Bronze, silver and gold tables exist. Bad rows are in quarantine with a reason.
- [ ] All DQ checks are `true`.
- [ ] A second run changes nothing (same counts and sums).
- [ ] The orchestration choice is recorded, and on HW the CPU/GPU runtime and cost are recorded.

## Record for the standards
`LAK-05` layer model and promotion rules. `DAT-08` data-quality gates. `ING-03` orchestration standard. `ING-06` pipeline engineering practices (idempotency). `LAK-07` when to use GPU acceleration (RAPIDS). `FIN-02` cost per pipeline run.

## Cleanup
`bin/spark-sql -e "DROP TABLE raw.orders_events PURGE; DROP TABLE curated.orders_clean PURGE; DROP TABLE curated.orders_quarantine PURGE; DROP TABLE consumption.daily_revenue PURGE"`
