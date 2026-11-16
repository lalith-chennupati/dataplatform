#!/usr/bin/env bash
# submit.sh <team> <name> <gpus> [priority-class]   - a 2-minute "training" job that requests fake GPUs
set -euo pipefail
team=$1 name=$2 gpus=$3 prio=${4:-research}
kubectl create -f - <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: $name
  namespace: $team
  labels: {kueue.x-k8s.io/queue-name: default, kueue.x-k8s.io/priority-class: $prio}
spec:
  suspend: true
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: train
          image: mirror.gcr.io/library/busybox:1.36
          command: ["sh", "-c", "echo training on $gpus GPU; sleep 120"]
          resources:
            requests: {cpu: 100m, memory: 64Mi, nvidia.com/gpu: "$gpus"}
            limits: {nvidia.com/gpu: "$gpus"}
YAML
