# E04 - Disaster recovery drill

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (lab S3 + kind) / DEMO (two OneFS Simulator clusters for SyncIQ) / HW (two sites) | 4 h | BCR, STO, PLT, NET | L01 core profile; kind cluster; A03 for SyncIQ; E03 completed. |

A DR plan that has not been run is a hypothesis. This drill fails a site while data is being written, measures how much data was lost (RPO) and how long it took to serve again (RTO), then fails back. **Untested here:** SyncIQ between two OneFS clusters and real DNS cutover (one VM, no OneFS).

## Steps

### Step 1 - [SIM] Write the runbook before the drill
List in order: who declares the disaster, how replication is broken, how the secondary is made writable, how clients are repointed (DNS, GitOps config, load balancer), which checks prove service is back, and how failback works. Time each step during the drill.

### Step 2 - [SIM] Run the drill
```bash
cd labs/env && ~/.venvs/aif/bin/python ops/dr_drill.py --interval 10 --run 25
```
Expected (my run):
```
  replication cycle copied 10 objects
  replication cycle copied 10 objects
PRIMARY SITE FAILED
failover: app now reads dr-secondary; newest replicated object orders/000019.json = {"order": 19}
RPO 4.7s (5 of 25 orders not replicated)   RTO 0.0s (automation only, excludes decision time)
failback: reverse sync copied 3 objects written during DR to dr-primary; 5 un-replicated orders on dr-primary must be reconciled
```
Rerun with `--interval 30` and `--interval 5`. The worst-case RPO is about one replication interval, which is the number to put in the standard, not the lucky case.

### Step 3 - [SIM] Redeploy the application from Git
The application side of DR is GitOps: the secondary cluster pulls the same manifests.
```bash
kubectl create ns dr-app
kubectl -n dr-app create deployment rag-api --image=mirror.gcr.io/library/nginx:1.27 --replicas=2
kubectl -n dr-app get deploy rag-api -o yaml > /tmp/rag-api.yaml        # in production this file lives in Git
kind create cluster --name aifactory-dr                                  # the "DR site" cluster
time (kubectl --context kind-aifactory-dr create ns dr-app && kubectl --context kind-aifactory-dr apply -f /tmp/rag-api.yaml \
      && kubectl --context kind-aifactory-dr -n dr-app rollout status deploy/rag-api)
```
Record the redeploy time. Then try to rebuild the C04/C05 setup (fake GPUs, Kueue queues) on `aifactory-dr` from the manifests in the repo: anything you have to do by hand is a gap in GitOps coverage.

### Step 4 - [DEMO] SyncIQ failover and failback
On two OneFS Simulator clusters: `isi sync policies create dr-finance sync /ifs/bu-finance <target-ip> /ifs/bu-finance --schedule "every 15 minutes"`, run it, write files on the source, then on the target `isi sync recovery allow-write dr-finance`. Repoint the SmartConnect zone (or DNS CNAME) to the target, mount from a client, and time it. Fail back with `isi sync recovery resync-prep dr-finance` on the original source, then reverse. Record RPO (last successful sync vs. failure time) and RTO.

### Step 5 - [HW] Full site drill
On two sites: replicate data (SyncIQ / ObjectScale geo-replication), restore registry and catalog (E03), redeploy inference from Git onto the DR GPU pool, cut over DNS for the inference endpoint, run the D03 and D05 tests against DR. Decide whether DR runs at full or reduced GPU capacity.

## Verify
- [ ] Runbook timed step by step.
- [ ] Worst-case RPO and RTO measured and compared with `BCR-02` targets.
- [ ] Application redeployed only from Git; manual steps listed as gaps.
- [ ] Failback done and un-replicated data reconciled.

## Record for the standards
`BCR-02` RPO/RTO. `BCR-03` DR site or degraded service. `BCR-06` DR test frequency. `STO-08` replication RPO per data class. `PLT-05` GitOps. `NET-09` DNS and naming for cutover.

## Cleanup
`labs/env/bin/s3 s3 rb --force s3://dr-primary`; `labs/env/bin/s3 s3 rb --force s3://dr-secondary`; `kubectl delete ns dr-app`; `kind delete cluster --name aifactory-dr`.
