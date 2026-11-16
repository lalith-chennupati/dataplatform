# B02 - Iceberg lakehouse on ObjectScale

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM / DEMO (Analytics Engine + ObjectScale) | 3 h | LAK, STO | B01 Step 2 |

In SIM, the Iceberg warehouse is `s3://warehouse/` on the lab S3. In DEMO, point the Iceberg catalog's `s3.endpoint` at ObjectScale (`$OBJ`) with a dedicated bucket per zone or per domain.

## Steps

### Step 1 - Create the zone model
```bash
cd labs/env
bin/trino --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.raw         WITH (location='s3://warehouse/raw');
CREATE SCHEMA IF NOT EXISTS iceberg.curated     WITH (location='s3://warehouse/curated');
CREATE SCHEMA IF NOT EXISTS iceberg.consumption WITH (location='s3://warehouse/consumption')"
```
| Zone | Contents | Who writes | Who reads |
|---|---|---|---|
| raw | as-landed copies, append-only | ingestion jobs | data engineers |
| curated | cleaned, conformed, deduplicated | pipelines (B04) | engineers, data scientists |
| consumption | aggregates/features for a use case | pipelines | analysts, apps, models |

### Step 2 - Land raw data, then curate it
```bash
bin/trino --execute "
CREATE OR REPLACE TABLE iceberg.raw.orders AS SELECT * FROM tpch.tiny.orders;
CREATE OR REPLACE TABLE iceberg.curated.orders WITH (partitioning = ARRAY['month(order_date)'], format = 'PARQUET') AS
SELECT orderkey AS order_id, (custkey % 1000) + 1 AS customer_id, totalprice AS amount, orderdate AS order_date, orderstatus AS status
FROM iceberg.raw.orders"
bin/s3 s3 ls --recursive s3://warehouse/curated/ | head      # data/ (Parquet, one folder per month) + metadata/ (JSON + Avro manifests)
bin/trino --execute "SELECT partition, record_count, file_count FROM iceberg.curated.\"orders\$partitions\" ORDER BY 1 LIMIT 5"
```

### Step 3 - Make changes and keep their history
```bash
bin/trino --execute "SELECT snapshot_id, operation, committed_at FROM iceberg.curated.\"orders\$snapshots\" ORDER BY committed_at"
# note the snapshot_id -> V1 (15000 rows)
bin/trino --execute "ALTER TABLE iceberg.curated.orders ADD COLUMN channel varchar"           # schema evolution, no rewrite
bin/trino --execute "UPDATE iceberg.curated.orders SET channel = 'web' WHERE order_id % 2 = 0"
bin/trino --execute "DELETE FROM iceberg.curated.orders WHERE status = 'P'"                    # deletes 363 rows
bin/trino --execute "SELECT snapshot_id, operation FROM iceberg.curated.\"orders\$snapshots\" ORDER BY committed_at"
```

### Step 4 - Time travel
```bash
bin/trino --execute "SELECT count(*) FROM iceberg.curated.orders"                              # 14637
bin/trino --execute "SELECT count(*) FROM iceberg.curated.orders FOR VERSION AS OF <V1>"       # 15000
bin/trino --execute "SELECT count(*) FROM iceberg.curated.orders FOR TIMESTAMP AS OF TIMESTAMP '<committed_at of V1>'"
```
Roll back the delete (optional): `bin/trino --execute "ALTER TABLE iceberg.curated.orders EXECUTE rollback_to_snapshot(<snapshot before DELETE>)"`. Use `CALL iceberg.system.rollback_to_snapshot('curated','orders',<id>)` on releases that have the procedure instead of the table command.

### Step 5 - Partition evolution
```bash
bin/trino --execute "ALTER TABLE iceberg.curated.orders SET PROPERTIES partitioning = ARRAY['year(order_date)', 'status']"
bin/trino --execute "INSERT INTO iceberg.curated.orders SELECT order_id + 1000000, customer_id, amount, order_date, status, 'store' FROM iceberg.curated.orders LIMIT 100"
bin/trino --execute "SELECT partition, record_count FROM iceberg.curated.\"orders\$partitions\" ORDER BY record_count LIMIT 3"
```
Old files keep the monthly layout. New files use the new spec. Queries do not change.

### Step 6 - Maintenance: compaction, snapshot expiry, orphan cleanup
```bash
bin/trino --execute "SELECT count(*) AS files, round(avg(file_size_in_bytes)/1024) AS avg_kb FROM iceberg.curated.\"orders\$files\""
bin/trino --execute "ALTER TABLE iceberg.curated.orders EXECUTE optimize(file_size_threshold => '128MB')"
bin/trino --execute "ALTER TABLE iceberg.curated.orders EXECUTE expire_snapshots(retention_threshold => '0s')"
bin/trino --execute "ALTER TABLE iceberg.curated.orders EXECUTE remove_orphan_files(retention_threshold => '0s')"
bin/trino --execute "SELECT count(*) FROM iceberg.curated.\"orders\$snapshots\""             # 1
bin/trino --execute "SELECT count(*) AS files FROM iceberg.curated.\"orders\$files\""
```
`0s` works because the lab catalog sets `iceberg.expire-snapshots.min-retention=0s`. In production keep the default 7 days (or your standard), because expiring a snapshot ends time travel to it.

### Step 7 - A consumption table
```bash
bin/trino --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.consumption WITH (location='s3://warehouse/consumption');
CREATE OR REPLACE TABLE iceberg.consumption.revenue_by_region_month AS
SELECT c.region, date_trunc('month', o.order_date) AS month, sum(o.amount) AS revenue
FROM iceberg.curated.orders o JOIN postgresql.crm.customers c USING (customer_id) GROUP BY 1, 2"
```

### Step 8 - Interoperability check
Read the same table from Spark (Data Processing Engine stand-in):
```bash
make up PROFILES="core spark"
bin/spark-sql -e "SELECT count(*) FROM curated.orders; SELECT * FROM curated.orders.snapshots"
```

## Verify
- [ ] Three zones exist with clear write/read ownership.
- [ ] Schema and partition evolution worked without rewriting the table.
- [ ] Time travel returns the earlier row count.
- [ ] Compaction reduced the file count. Expiry left one snapshot.
- [ ] Spark and Trino read the same table.

## Record for the standards
`LAK-02` table format (Iceberg, Parquet, compression). `LAK-05` zone model. `LAK-06` file format and partitioning conventions, plus the maintenance schedule (compaction, snapshot retention, orphan cleanup). `ING-07` schema evolution policy. `LAK-03` catalog of record. `DAT-09` retention, including the time-travel window.

## Cleanup
Keep the tables for B03-B05. To drop everything: `bin/trino --execute "DROP TABLE iceberg.raw.orders; DROP TABLE iceberg.consumption.revenue_by_region_month"`.
