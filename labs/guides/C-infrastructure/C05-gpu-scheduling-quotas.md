# C05 - GPU scheduling, quotas and fair share

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (kind + Kueue + fake GPUs) / HW (Kueue or NVIDIA Run:ai on a GPU cluster, or Slurm from C03) | 3 h | CMP, FIN, OPS | L01 kind cluster. HW: C04. |

Three teams share 8 GPUs. Each team has a guaranteed quota (`nominalQuota`) and can borrow idle GPUs from the others in the same cohort. When the owner wants its GPUs back, Kueue preempts the borrower. Inside a team, higher-priority work preempts lower-priority work. In SIM the GPUs are fake: `kind/fake-gpus.sh` advertises `nvidia.com/gpu: 8` on the `gpu-sim` worker, so the scheduler logic is real but the pods only sleep. Steps 1-6 were run on my VM with Kueue v0.20.6. Kueue v0.20+ serves the `kueue.x-k8s.io/v1beta2` API (`cohortName`); older releases use `v1beta1` (`cohort`).

| Team | Guaranteed GPUs | May borrow up to |
|---|---|---|
| team-a | 4 | 4 |
| team-b | 2 | 6 |
| team-c | 2 | 0 (never borrows) |

## Steps

### Step 1 - Install Kueue and fake GPUs
```bash
cd labs/env
kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/v0.20.6/manifests.yaml
kubectl -n kueue-system rollout status deploy/kueue-controller-manager --timeout=180s
kind/fake-gpus.sh 8                   # "8 fake GPUs allocatable on aifactory-lab-worker2"
```
HW: skip `fake-gpus.sh`; the device plugin from C04 advertises the real GPUs. The ResourceFlavor in `queues.yaml` selects nodes with `pool: gpu-sim`; change `nodeLabels` to e.g. `nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3`.

### Step 2 - Queues and teams
```bash
kubectl apply -f kind/kueue/queues.yaml -f kind/kueue/team-namespaces.yaml
kubectl get clusterqueues,localqueues -A
```
Read `kind/kueue/queues.yaml`: one ResourceFlavor, two WorkloadPriorityClasses (`prod-inference` 1000, `research` 100), and three ClusterQueues in cohort `ai-factory` with `reclaimWithinCohort: Any` and `withinClusterQueue: LowerPriority`.

Helper used below: `kind/kueue/submit.sh <team> <job> <gpus> [priority-class]` creates a suspended Job that Kueue admits when quota allows.
```bash
W() { kubectl get workloads -A -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,PRIO:.spec.priority,ADMITTED:.status.conditions[?(@.type=="Admitted")].status,EVICTED:.status.conditions[?(@.type=="Evicted")].reason'; }
```

### Step 3 - Borrowing
```bash
kind/kueue/submit.sh team-a a1 4
kind/kueue/submit.sh team-a a2 4      # 4 above team-a's quota: borrowed from idle team-b/team-c GPUs
sleep 10; W
```
Expected: both `a1` and `a2` `ADMITTED True`. team-a uses all 8 GPUs.

### Step 4 - Reclaim
```bash
kind/kueue/submit.sh team-b b1 2
kind/kueue/submit.sh team-c c1 2
sleep 15; W
```
Expected (observed):
```
team-a   job-a1-...   100    False      Preempted
team-a   job-a2-...   100    True       <none>
team-b   job-b1-...   100    True       <none>
team-c   job-c1-...   100    True       <none>
```
team-b and team-c reclaimed their guaranteed GPUs, so one of team-a's borrowing jobs was preempted and requeued. In production that job must restart from its last checkpoint (`BCR-07`, A10).

### Step 5 - Hard cap
```bash
kind/kueue/submit.sh team-c c2 2; sleep 10; W
kubectl get clusterqueue -o custom-columns=NAME:.metadata.name,PENDING:.status.pendingWorkloads,ADMITTED:.status.admittedWorkloads
```
Expected: `c2` pending (team-c has `borrowingLimit: 0`), team-a also has 1 pending (`a1`).

### Step 6 - Priority preemption inside a team
```bash
kind/kueue/submit.sh team-c c3 2 prod-inference; sleep 15
kubectl get workloads -n team-c -o custom-columns='NAME:.metadata.name,PRIO:.spec.priority,ADMITTED:.status.conditions[?(@.type=="Admitted")].status,PREEMPTED:.status.conditions[?(@.type=="Preempted")].reason'
```
Expected (observed): `c3` (priority 1000) admitted; `c1` (100) `Preempted` with reason `InClusterQueue`.

### Step 7 - Queue wait time
The standard needs a queue wait-time metric. Per workload:
```bash
kubectl get workloads -A -o json | python3 -c "
import sys, json, datetime as dt
p = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
for w in json.load(sys.stdin)['items']:
    c = {x['type']: x for x in w['status'].get('conditions', [])}
    a = c.get('Admitted', {})
    print(w['metadata']['namespace'], w['metadata']['name'],
          (p(a['lastTransitionTime']) - p(w['metadata']['creationTimestamp'])).seconds if a.get('status') == 'True' else 'pending')"
kubectl get --raw /apis/visibility.kueue.x-k8s.io/v1beta2/clusterqueues/team-c/pendingworkloads   # queue position per pending job
```
For dashboards, scrape the Kueue controller metrics (service `kueue-controller-manager-metrics-service`, port 8443, needs a ServiceMonitor or bearer token) and use its admission wait-time histogram. Check the metric names for your Kueue version on `/metrics`. Add a panel to C08 and an alert when p90 wait exceeds your SLO (`OPS-04`).

### Step 8 - [HW] Slurm and Run:ai equivalents
- Slurm: partitions per pool, `sacctmgr add qos research Priority=100 Preempt=... PreemptMode=requeue`, `GrpTRES=gres/gpu=4` per account for guaranteed quota, `PriorityType=priority/multifactor` with `PriorityWeightFairshare` for fair share. Check with `sshare -a`, `sprio`, `squeue --start`.
- NVIDIA Run:ai: departments and projects with GPU quota, over-quota borrowing and fair share are configured in the UI/API. Repeat Steps 3-6 and compare.

### Step 9 - Write the policy
Per team: guaranteed GPUs, borrowing limit, priority classes allowed, who may submit `prod-inference`, maximum job duration, and what happens to idle allocations (`CMP-08`).

## Verify
- [ ] Borrowing, reclaim, hard cap and priority preemption each observed and saved (`W > ../evidence/c05-stepN.txt`).
- [ ] A queue wait-time number exists per workload, and a dashboard/alert plan for it.
- [ ] The quota and preemption policy table is filled in.

## Record for the standards
`CMP-07` quotas, priorities and preemption. `CMP-06` scheduler choice (Kueue, Run:ai, Slurm). `CMP-08` idle GPU handling. `FIN-02` GPU-hours as the metered unit (E05). `OPS-04` queue wait-time SLO.

## Cleanup
```bash
kubectl delete ns team-a team-b team-c
kubectl delete -f kind/kueue/queues.yaml
# optional: kubectl delete -f https://github.com/kubernetes-sigs/kueue/releases/download/v0.20.6/manifests.yaml
```
