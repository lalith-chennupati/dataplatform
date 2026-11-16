# B01 - Federated SQL with the Data Analytics Engine

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Trino 476) / DEMO (Dell Data Analytics Engine) | 2 h | LAK, DAT | L01 (`make up`) |

The Dell Data Analytics Engine is based on Starburst (Trino). Everything below is standard Trino SQL. On the Dell engine, use its web UI or JDBC endpoint instead of `bin/trino`, and replace the catalog names with the ones your admin created.

## Steps

### Step 1 - Look at the catalogs
```bash
cd labs/env
bin/trino --execute "SHOW CATALOGS"                     # iceberg, postgresql, system, tpch
bin/trino --execute "SHOW TABLES FROM postgresql.crm"   # customers
cat trino/catalog/postgresql.properties                 # a catalog = connector + connection settings
```
[DEMO] In the Dell engine, open *Catalogs* and list the connectors available (PowerScale/HDFS, S3/ObjectScale, RDBMS, Elasticsearch, etc.). Record them.

### Step 2 - Create "sales" data in the lakehouse
```bash
bin/trino --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.curated WITH (location='s3://warehouse/curated');
CREATE OR REPLACE TABLE iceberg.curated.orders WITH (partitioning = ARRAY['month(order_date)']) AS
SELECT orderkey AS order_id, (custkey % 1000) + 1 AS customer_id, totalprice AS amount,
       orderdate AS order_date, orderstatus AS status
FROM tpch.tiny.orders"
```
Expected: `CREATE TABLE: 15000 rows`. The sales facts now live as Iceberg/Parquet on S3. Customers stay in PostgreSQL.

### Step 3 - Federated join, no copy
```bash
bin/trino --execute "
SELECT c.region, count(*) AS orders, round(sum(o.amount)) AS revenue
FROM iceberg.curated.orders o
JOIN postgresql.crm.customers c ON o.customer_id = c.customer_id
GROUP BY c.region ORDER BY revenue DESC"
```
Expected: four rows (NA, EMEA, APJ, LATAM), about 3,700 orders each.

### Step 4 - See what is pushed down to the source
```bash
bin/trino --execute "EXPLAIN SELECT name FROM postgresql.crm.customers WHERE region = 'EMEA'" | grep -i -A2 "TableScan"
```
The `region = 'EMEA'` filter appears inside the PostgreSQL table handle, so PostgreSQL does the filtering and only matching rows cross the network. Then run `EXPLAIN ANALYZE` on the Step 3 query and note the rows and bytes read from each source.

### Step 5 - Compare with an ETL copy
```bash
time bin/trino --execute "CREATE OR REPLACE TABLE iceberg.curated.customers_copy AS SELECT * FROM postgresql.crm.customers"
time bin/trino --execute "SELECT c.region, round(sum(o.amount)) FROM iceberg.curated.orders o JOIN iceberg.curated.customers_copy c ON o.customer_id = c.customer_id GROUP BY 1"
time bin/trino --execute "SELECT c.region, round(sum(o.amount)) FROM iceberg.curated.orders o JOIN postgresql.crm.customers c ON o.customer_id = c.customer_id GROUP BY 1"
```
Now change the source:
```bash
docker compose exec -T postgres psql -U postgres -d lab -c "UPDATE crm.customers SET region='NA' WHERE customer_id <= 50"
```
Run both joins again. The federated query reflects the change immediately. The copy is stale until the ETL runs again.

### Step 6 - Write the decision rule
Fill in this table in the evidence log. It becomes the `LAK-04` answer:

| Criterion | Federate | Ingest (copy into Iceberg) |
|---|---|---|
| Freshness needed | real-time from source | batch window acceptable |
| Query frequency / concurrency | low-medium | high (dashboards, ML training) |
| Source system load tolerance | source can take the queries | source must be protected |
| Data volume scanned | small, filter pushdown works | large scans / joins |
| Governance | source owns access | lakehouse policies apply (B03) |

## Verify
- [ ] The federated query returns correct totals. They match the copy-based query before the source update.
- [ ] The pushdown is visible in `EXPLAIN`.
- [ ] Timings for federated vs. copied queries are recorded.
- [ ] The federation-vs-ingestion rule is written.

## Record for the standards
`LAK-04` federation policy. `LAK-01` which engine is the SQL standard. `DAT-06` which catalogs are registered.

## Cleanup
```bash
bin/trino --execute "DROP TABLE IF EXISTS iceberg.curated.customers_copy"
docker compose exec -T postgres psql -U postgres -d lab -c "UPDATE crm.customers SET region=(ARRAY['NA','EMEA','APJ','LATAM'])[1 + customer_id % 4] WHERE customer_id <= 50"
```
Keep `iceberg.curated.orders`. B02-B05 use it.
