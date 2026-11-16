# A06 - PowerScale for Kubernetes AI jobs

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (OneFS Simulator + kind) / HW | 4 h | STO, PLT | A01, A02; L01 Step 5 (`make kind-up`) |

## Prerequisites
- The kind nodes can reach `$PS` (same L2/L3 network as the Docker host) and have an NFS client:
  ```bash
  for n in $(kind get nodes --name aifactory-lab); do docker exec $n bash -c "apt-get update -qq && apt-get install -y -qq nfs-common"; done
  ```
- An access zone and base path for CSI, e.g. zone `System`, path `/ifs/data/csi`: `ssh root@$PS mkdir -p /ifs/data/csi`.

## Steps

### Step 1 - Install the CSI PowerScale driver
```bash
helm repo add dell https://dell.github.io/helm-charts && helm repo update
kubectl create namespace isilon
cat > isilon-creds.yaml <<EOT
isilonClusters:
  - clusterName: "ps-lab"
    username: "root"
    password: "<root password>"
    endpoint: "$PS"
    endpointPort: "8080"
    isDefault: true
    skipCertificateValidation: true
    isiPath: "/ifs/data/csi"
EOT
kubectl create secret generic isilon-creds -n isilon --from-file=config=isilon-creds.yaml
kubectl create secret generic isilon-certs-0 -n isilon --from-literal=cert-0=""
helm show values dell/csi-isilon > csi-values.yaml     # review: replication, authorization, snapshot, healthMonitor
helm install isilon dell/csi-isilon -n isilon -f csi-values.yaml
kubectl get pods -n isilon -w        # controller(s) and one node pod per worker become Running
```
Alternatively, install with the **Container Storage Modules (CSM) Operator** (`dell/container-storage-modules-operator`). It installs the driver together with the Authorization / Observability / Replication modules.

### Step 2 - StorageClass and snapshot class
```yaml
# sc.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata: {name: powerscale-ai}
provisioner: csi-isilon.dellemc.com
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
parameters:
  AccessZone: System
  IsiPath: /ifs/data/csi
  RootClientEnabled: "false"
  # AzServiceIP: <SmartConnect name of the zone>
---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata: {name: powerscale-snap}
driver: csi-isilon.dellemc.com
deletionPolicy: Delete
parameters: {IsiPath: /ifs/data/csi}
```
`kubectl apply -f sc.yaml`. VolumeSnapshots need the external-snapshotter CRDs and controller. Install them from `kubernetes-csi/external-snapshotter` if `kubectl get crd volumesnapshots.snapshot.storage.k8s.io` is empty.

### Step 3 - Shared dataset volume (RWX)
```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: dataset, namespace: ml-team}
spec:
  accessModes: [ReadWriteMany]
  storageClassName: powerscale-ai
  resources: {requests: {storage: 5Gi}}
```
```bash
kubectl create ns ml-team && kubectl apply -f pvc.yaml
kubectl get pvc -n ml-team               # Bound
ssh root@$PS ls /ifs/data/csi            # a k8s-<id> directory with a quota
```

### Step 4 - Parallel data-loader job
```yaml
# loader.yaml - 4 pods write shards, then each pod reads all shards
apiVersion: batch/v1
kind: Job
metadata: {name: loader, namespace: ml-team}
spec:
  completions: 4
  parallelism: 4
  completionMode: Indexed
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: w
          image: mirror.gcr.io/library/python:3.12-slim
          command: ["python", "-c"]
          args:
            - |
              import os, time, glob, hashlib
              i = os.environ["JOB_COMPLETION_INDEX"]
              with open(f"/data/shard-{i}.bin", "wb") as f: f.write(os.urandom(50 * 2**20))
              time.sleep(20)
              print(i, sorted(os.path.basename(p) for p in glob.glob("/data/shard-*.bin")))
          volumeMounts: [{name: d, mountPath: /data}]
      volumes: [{name: d, persistentVolumeClaim: {claimName: dataset}}]
```
```bash
kubectl apply -f loader.yaml && kubectl wait -n ml-team --for=condition=complete job/loader --timeout=300s
kubectl logs -n ml-team -l job-name=loader      # every pod lists all 4 shards
```

### Step 5 - Snapshot and restore the PVC
```yaml
# snap.yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata: {name: dataset-snap, namespace: ml-team}
spec: {volumeSnapshotClassName: powerscale-snap, source: {persistentVolumeClaimName: dataset}}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: dataset-restored, namespace: ml-team}
spec:
  accessModes: [ReadWriteMany]
  storageClassName: powerscale-ai
  resources: {requests: {storage: 5Gi}}
  dataSource: {name: dataset-snap, kind: VolumeSnapshot, apiGroup: snapshot.storage.k8s.io}
```
`kubectl apply -f snap.yaml`, then mount `dataset-restored` in a pod and list the shards.

### Step 6 - Expand the volume
`kubectl patch pvc dataset -n ml-team -p '{"spec":{"resources":{"requests":{"storage":"8Gi"}}}}'`. Check that `isi quota quotas list | grep k8s` shows the new hard limit.

### Step 7 - [DEMO/HW] Tenant limits with CSM Authorization
1. Deploy CSM Authorization (proxy server) with the CSM Operator or Helm, following the Dell CSM docs for your release.
2. Create a *storage* entry for `ps-lab`, a *role* `ml-team-quota` with a 10 GiB limit on `/ifs/data/csi`, and a *tenant* `ml-team` bound to that role. Generate the tenant token and install it in the `isilon` namespace.
3. Request a 20 Gi PVC. Expected: provisioning is denied because it exceeds the tenant quota.

### Step 8 - [DEMO/HW] Observability module
Enable CSM Observability and scrape its metrics with Prometheus (`make up PROFILES="core obs"` or kube-prometheus-stack). Chart PVC capacity and I/O per namespace in Grafana.

## Verify
- [ ] An RWX PVC is shared by 4 pods. Every pod sees every shard.
- [ ] Snapshot -> restored PVC contains the data.
- [ ] Volume expansion updates the OneFS quota.
- [ ] *(DEMO/HW)* A request over the CSM Authorization quota is denied.

## Record for the standards
`STO-11` CSI/CSM integration: default StorageClass parameters, snapshot class, reclaim policy. `PLT-08` developer self-service (PVCs on demand).

## Cleanup
`kubectl delete ns ml-team`, then `helm uninstall isilon -n isilon`.
