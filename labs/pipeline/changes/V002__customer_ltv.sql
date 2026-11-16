CREATE TABLE IF NOT EXISTS iceberg.${env}_consumption.customer_ltv (customer_id BIGINT, orders BIGINT, lifetime_value DOUBLE, first_order DATE, last_order DATE);
