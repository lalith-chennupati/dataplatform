#!/usr/bin/env bash
# Smoke test for the SIM lab environment. Exits non-zero on the first failure.
set -euo pipefail
cd "$(dirname "$0")"
pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; exit 1; }
running() { docker compose --profile "$1" ps --status running --services 2>/dev/null | grep -qx "$2"; }

echo "core:"
bin/s3 s3 ls >/dev/null && pass "S3 endpoint lists buckets" || fail "S3 endpoint"
echo smoke > .smoke.txt
S3_USER=finance bin/s3 s3 cp /work/.smoke.txt s3://bu-finance/.smoke.txt >/dev/null && pass "tenant 'finance' writes its own bucket" || fail "finance write"
if S3_USER=finance bin/s3 s3 cp /work/.smoke.txt s3://bu-research/.smoke.txt >/dev/null 2>&1; then fail "finance must NOT write bu-research"; else pass "cross-tenant write denied"; fi
rm -f .smoke.txt
bin/trino --execute "SELECT count(*) FROM postgresql.crm.customers" 2>/dev/null | grep -q '"1000"' && pass "Trino -> PostgreSQL federation" || fail "Trino postgresql catalog"
bin/trino --execute "CREATE SCHEMA IF NOT EXISTS iceberg.smoke WITH (location='s3://warehouse/smoke'); CREATE OR REPLACE TABLE iceberg.smoke.t AS SELECT 1 AS x; SELECT x FROM iceberg.smoke.t" 2>/dev/null | grep -q '"1"' && pass "Trino -> Iceberg REST -> S3" || fail "Trino iceberg catalog"
curl -sf localhost:9200/_cluster/health | grep -qv '"status":"red"' && pass "Elasticsearch healthy" || fail "Elasticsearch"

if running spark spark; then
  echo "spark:"
  bin/spark-sql -e "SELECT x FROM lake.smoke.t" 2>/dev/null | grep -qx 1 && pass "Spark reads the Iceberg table Trino wrote" || fail "Spark iceberg"
fi
if running infra redfish; then
  echo "infra:"
  curl -sf localhost:8000/redfish/v1/Systems | grep -q Members && pass "Redfish mockup answers" || fail "Redfish mockup"
fi
if running ai ollama; then
  echo "ai:"
  curl -sf localhost:11434/api/tags >/dev/null && pass "Ollama API up" || fail "Ollama"
  curl -sf localhost:5000/health >/dev/null && pass "MLflow up" || fail "MLflow"
fi
if running obs prometheus; then
  echo "obs:"
  curl -sf localhost:9090/-/ready >/dev/null && pass "Prometheus ready" || fail "Prometheus"
  curl -sf localhost:3000/api/health >/dev/null && pass "Grafana up" || fail "Grafana"
fi
echo "all checks passed"
