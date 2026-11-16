# E05 - Chargeback and capacity

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (lab S3 + sample scheduler export) / DEMO (OneFS SmartQuotas, ObjectScale metering) / HW (DCGM on GPU nodes) | 3 h | FIN, OPS, STO, CMP | L01 core profile; C05 (queues) and C08 (Prometheus) recommended. |

A shared AI Factory is only sustainable if each team sees what it uses. This lab builds a monthly showback from GPU-hours, storage and tokens, and shows how unlabelled workloads break it. The rates in [rates.yaml](../../env/ops/rates.yaml) are placeholders; derive yours from the funding model. **Untested here:** OneFS SmartQuotas reports, ObjectScale metering and DCGM on real GPUs.

## Steps

### Step 1 - [SIM] Choose the cost units
Read [rates.yaml](../../env/ops/rates.yaml): GPU-hour (allocated, not utilised), storage TB-month, million tokens. Decide whether idle reserved GPUs are charged to the owner of the reservation (they should be, or nobody releases them).

### Step 2 - [SIM] Run the showback
```bash
cd labs/env && ~/.venvs/aif/bin/python ops/showback.py
```
Expected (sample data): team-a about 528 GPU-h, team-b 80, team-c 342.5, `UNALLOCATED 107.0`, and the two unlabelled workloads with the labels they are missing (`10% of GPU-hours are unallocated`). Storage is measured live from the lab buckets, so it is tiny.

### Step 3 - [SIM] Enforce labels at admission
Unlabelled usage cannot be charged. Reject it before it runs:
```bash
kubectl apply -f - <<'Y'
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: require-cost-labels}
spec:
  failurePolicy: Fail
  matchConstraints: {resourceRules: [{apiGroups: ["batch"], apiVersions: ["v1"], operations: ["CREATE"], resources: ["jobs"]}]}
  validations:
  - expression: "has(object.metadata.labels) && ['cost-center','owner','project'].all(l, l in object.metadata.labels)"
    message: "jobs need cost-center, owner and project labels"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: require-cost-labels}
spec: {policyName: require-cost-labels, validationActions: [Deny], matchResources: {namespaceSelector: {matchExpressions: [{key: kubernetes.io/metadata.name, operator: In, values: [team-a, team-b]}]}}}
Y
kubectl -n team-a create job nolabel --image=busybox -- true          # expect: denied
```
Then add the labels (`kubectl create job --dry-run=client -o yaml`, edit, apply) and confirm it is admitted.

### Step 4 - [SIM] Use real data
Export GPU allocation from Kueue (`kubectl get workloads -A -o json`: admission time, finish time, `nvidia.com/gpu` requests) or Slurm (`sacct -X --format=Account,AllocTRES%40,Elapsed`), convert to the CSV columns of [usage-sample.csv](../../env/ops/usage-sample.csv), then `ops/showback.py --gpu-usage <file>`. Add token counts per tenant from the LLM gateway logs with `--tokens-per-tenant '{"team-c": 4200000}'`.

### Step 5 - [DEMO] Storage metering
OneFS: `isi quota quotas create /ifs/bu-finance directory --hard-threshold 10T --advisory-threshold 8T` and `isi quota reports create`; read usage with `isi quota quotas list --format json`. ObjectScale: bucket and namespace metering from the management API or UI. Feed both into the showback instead of the S3 listing.

### Step 6 - [HW] GPU utilisation vs. allocation
With DCGM exporter (C08) on real GPUs, add `DCGM_FI_DEV_GPU_UTIL` averaged per pod. Show allocated GPU-hours next to utilised GPU-hours per team: teams below ~40 % utilisation are candidates for MIG or time-slicing (C04).

### Step 7 - [SIM] Capacity trigger
From the showback trend, compute months until GPU allocation exceeds 80 % of capacity and storage exceeds 80 % of usable TB. Those dates are the procurement triggers for the standard.

## Verify
- [ ] Showback produced per tenant with an unallocated line.
- [ ] Jobs without cost labels denied at admission.
- [ ] *(DEMO/HW)* Quota reports and DCGM utilisation feed the report.
- [ ] Capacity trigger dates computed.

## Record for the standards
`FIN-01` funding model. `FIN-02` metered cost units. `FIN-03` mandatory labels. `FIN-05` capacity trigger. `FIN-07` budgets and alerts per team. `STO-07` quotas per tenant. `OPS-03` GPU telemetry.

## Cleanup
`kubectl delete validatingadmissionpolicybinding require-cost-labels; kubectl delete validatingadmissionpolicy require-cost-labels`.
