#!/usr/bin/env bash
# Advertise N fake nvidia.com/gpu on the kind 'gpu-sim' worker so GPU quota/scheduling labs (C05) run without GPUs.
set -euo pipefail
N="${1:-8}"; NODE="${NODE:-aifactory-lab-worker2}"
kubectl proxy --port=8011 >/dev/null 2>&1 & P=$!; trap 'kill $P' EXIT; sleep 2
curl -sf -o /dev/null -H 'Content-Type: application/json-patch+json' -X PATCH \
  "http://127.0.0.1:8011/api/v1/nodes/$NODE/status" \
  -d "[{\"op\":\"add\",\"path\":\"/status/capacity/nvidia.com~1gpu\",\"value\":\"$N\"}]"
sleep 3; kubectl get node "$NODE" -o jsonpath='{.status.allocatable.nvidia\.com/gpu}{" fake GPUs allocatable on '"$NODE"'\n"}'
