#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for s in silver gold; do bin/spark-sql -f /opt/lab/$s.sql; done
bin/spark-sql -f /opt/lab/dq.sql | tee /tmp/dq.txt; ! grep -q false /tmp/dq.txt
