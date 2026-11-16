# C04 - GPUs on Kubernetes

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| HW (PowerEdge XE / R-series GPU node in a Kubernetes cluster). SIM covers Steps 1-2 only. | 4 h | CMP, PLT, OPS | L01 (kind cluster), `helm`. HW: C03 or any Kubernetes cluster with an NVIDIA GPU node. |

The NVIDIA GPU Operator installs the driver, container toolkit, device plugin, GPU Feature Discovery, DCGM exporter and MIG manager as Kubernetes DaemonSets, controlled by one `ClusterPolicy`. In SIM you install the operator on kind to see the control flow; without an NVIDIA PCI device it deploys only NFD and the operator. The MIG, time-slicing and DCGM steps need a real GPU and were **not run here**. Check MIG profile names against your GPU model (`nvidia-smi mig -lgip`).

## Steps

### Step 1 - [SIM/HW] Install the GPU Operator
```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia && helm repo update
helm search repo nvidia/gpu-operator                    # record the chart version and pin it
# SIM (kind): no driver/toolkit on kind nodes
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace \
  --version <pinned> --set driver.enabled=false --set toolkit.enabled=false --wait
# HW: leave driver.enabled=true unless the OS image already has the driver (Omnia can install it, C03)
kubectl get pods -n gpu-operator
kubectl get clusterpolicy -o custom-columns=NAME:.metadata.name,STATE:.status.state
```
Expected SIM (checked on my VM with chart v26.7.2): `gpu-operator` and the `node-feature-discovery` master/worker/gc pods `Running`, ClusterPolicy `ready`, and no device-plugin/DCGM pods because no node has an NVIDIA PCI device.
Expected HW: also `nvidia-driver-daemonset`, `nvidia-container-toolkit-daemonset`, `nvidia-device-plugin-daemonset`, `gpu-feature-discovery`, `nvidia-dcgm-exporter`, `nvidia-mig-manager`, and `nvidia-cuda-validator` `Completed`.

### Step 2 - [SIM/HW] Node feature discovery labels
```bash
kubectl get node <node> -o json | python3 -c "import sys,json;l=json.load(sys.stdin)['metadata']['labels'];[print(k,v) for k,v in sorted(l.items()) if 'pci-10de' in k or 'nvidia.com' in k or 'kernel-version.full' in k]"
```
SIM: only `kernel-version.full` and non-NVIDIA PCI labels (10de is NVIDIA's PCI vendor ID). HW: `feature.node.kubernetes.io/pci-10de.present=true`, `nvidia.com/gpu.product`, `nvidia.com/gpu.count`, `nvidia.com/gpu.memory`, `nvidia.com/mig.capable`. Use these labels, not hostnames, in node selectors.

### Step 3 - [HW] First GPU pod
```bash
kubectl run cuda-smoke --rm -it --restart=Never --image=nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04 \
  --overrides='{"spec":{"containers":[{"name":"c","image":"nvcr.io/nvidia/cuda:12.4.1-base-ubuntu22.04","command":["nvidia-smi","-L"],"resources":{"limits":{"nvidia.com/gpu":1}}}]}}'
kubectl describe node <gpu-node> | grep -A3 'nvidia.com/gpu'
```
Expected: one GPU listed. A pod without a GPU limit must **not** see any GPU (check with the same image and no limit).

### Step 4 - [HW] MIG
```bash
kubectl label node <gpu-node> nvidia.com/mig.config=all-1g.10gb --overwrite   # profile names depend on GPU (H100 80GB: all-1g.10gb, all-3g.40gb, all-balanced)
kubectl -n gpu-operator logs -l app=nvidia-mig-manager --tail=20               # wait for "success"
kubectl get node <gpu-node> -o jsonpath='{.metadata.labels.nvidia\.com/mig\.config\.state}{"\n"}'   # success
kubectl describe node <gpu-node> | grep nvidia.com/                            # e.g. nvidia.com/gpu: 56 with strategy single
```
Run 7 inference pods that each request one `nvidia.com/gpu` and check they land on separate MIG slices (`nvidia-smi -L` inside each). Note that changing the MIG layout drains GPU pods on that node. Record how long the reconfiguration took.

### Step 5 - [HW] Time-slicing
```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata: {name: time-slicing, namespace: gpu-operator}
data:
  any: |-
    version: v1
    sharing:
      timeSlicing:
        renameByDefault: false
        resources:
          - {name: nvidia.com/gpu, replicas: 4}
YAML
kubectl patch clusterpolicy cluster-policy --type merge -p '{"spec":{"devicePlugin":{"config":{"name":"time-slicing","default":"any"}}}}'
kubectl label node <gpu-node> nvidia.com/mig.config=all-disabled --overwrite
kubectl describe node <gpu-node> | grep nvidia.com/gpu        # capacity = physical GPUs x 4
```
Run 4 pods per GPU. Measure tokens/s or images/s per pod with 1, 2 and 4 pods sharing one GPU. Time-slicing gives **no memory or fault isolation**: one pod can OOM the others. MIG does isolate. Write that down next to the numbers.

### Step 6 - [HW] DCGM metrics per namespace
```bash
kubectl -n gpu-operator port-forward svc/nvidia-dcgm-exporter 9400:9400 &
curl -s localhost:9400/metrics | grep -E '^DCGM_FI_DEV_GPU_UTIL|^DCGM_FI_DEV_FB_USED' | head
```
The exporter labels each metric with `namespace` and `pod` of the workload using the GPU. Add the exporter as a Prometheus target (C08) and build a panel `avg by (namespace) (DCGM_FI_DEV_GPU_UTIL)`. This is the input for chargeback (E05) and idle-GPU policy (`CMP-08`).

### Step 7 - Decide the sharing policy
Fill in a table: workload class (training, batch inference, interactive notebooks, small online inference) x sharing mode (whole GPU, MIG profile, time-slicing, MPS) with the reason.

## Verify
- [ ] Operator installed from a pinned chart version; ClusterPolicy `ready`.
- [ ] *(HW)* A GPU pod runs; a pod without a GPU limit sees no GPU.
- [ ] *(HW)* MIG and time-slicing both tested, with throughput numbers.
- [ ] *(HW)* GPU utilisation is visible per namespace in Prometheus/Grafana.

## Record for the standards
`CMP-05` GPU sharing policy per workload class. `PLT-03` driver/CUDA/operator versions. `PLT-02` approved AI software stack on Kubernetes. `CMP-08` utilisation target and idle-GPU handling. `OPS-03` DCGM metrics that must be collected.

## Cleanup
```bash
helm uninstall gpu-operator -n gpu-operator && kubectl delete ns gpu-operator
# HW: kubectl label node <gpu-node> nvidia.com/mig.config=all-disabled --overwrite
```
