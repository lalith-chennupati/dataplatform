-- Trino SQL. ${env} and ${bucket} come from environments.yaml. Migrations must be additive so older releases can be rolled back to.
CREATE SCHEMA IF NOT EXISTS iceberg.${env}_raw WITH (location = 's3://${bucket}/raw');
CREATE SCHEMA IF NOT EXISTS iceberg.${env}_curated WITH (location = 's3://${bucket}/curated');
CREATE SCHEMA IF NOT EXISTS iceberg.${env}_consumption WITH (location = 's3://${bucket}/consumption');
CREATE TABLE IF NOT EXISTS iceberg.${env}_raw.orders_events (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status VARCHAR, _ingested_at TIMESTAMP(6) WITH TIME ZONE);
CREATE TABLE IF NOT EXISTS iceberg.${env}_curated.orders_clean (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status VARCHAR, _ingested_at TIMESTAMP(6) WITH TIME ZONE) WITH (partitioning = ARRAY['month(order_date)']);
CREATE TABLE IF NOT EXISTS iceberg.${env}_curated.orders_quarantine (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE, status VARCHAR, _ingested_at TIMESTAMP(6) WITH TIME ZONE, reason VARCHAR);
CREATE TABLE IF NOT EXISTS iceberg.${env}_consumption.daily_revenue (order_date DATE, status VARCHAR, orders BIGINT, revenue DOUBLE);
