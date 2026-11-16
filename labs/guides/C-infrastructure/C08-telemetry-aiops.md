# C08 - Infrastructure telemetry and AIOps

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Prometheus + Grafana + simulated exporters) / DEMO (APEX AIOps, InsightIQ) / HW | 3 h | OPS, CMP, STO, NET | L01 with `infra` and `obs` profiles. C01 for iDRAC telemetry. |

In production the metrics come from the iDRAC telemetry streaming / Redfish, the NVIDIA DCGM exporter (C04), OneFS (InsightIQ or a OneFS Prometheus exporter), switch telemetry (SONiC gNMI / streaming telemetry), and Dell APEX AIOps (formerly CloudIQ) for health scores and capacity forecasts. In SIM, `telemetry` is one exporter: it reads real values from the Redfish mockup and simulates DCGM, storage-quota and switch metrics so you can inject faults. Prometheus loads `prometheus/alerts.yml`, and Grafana is provisioned with the "AI Factory infrastructure health (SIM)" dashboard.

## Steps

### Step 1 - Start the stack
```bash
cd labs/env && make up PROFILES="core infra obs"
curl -s localhost:9101/metrics | head
curl -s localhost:9090/api/v1/targets | python3 -c "import sys,json;[print(t['labels']['job'],t['health']) for t in json.load(sys.stdin)['data']['activeTargets']]"
```
Expected: metric lines such as `redfish_power_consumed_watts{node="xe-node-01"} 344` and `DCGM_FI_DEV_GPU_TEMP{...,gpu="0",...}`. Target `infra-sim` is `up`.

### Step 2 - Dashboard
Open Grafana at `http://localhost:3000` -> Dashboards -> AI Factory -> "AI Factory infrastructure health (SIM)". Panels: firing alerts, mean GPU utilisation, storage quota, back-end links, GPU temperature and SM clock, node power from iDRAC, PFC pause rate. Add one panel of your own (e.g. `max by (gpu) (DCGM_FI_DEV_POWER_USAGE)`).

### Step 3 - Inject faults and watch the alerts
```bash
curl -s 'localhost:9101/fault?gpu=3&temp=96'       # thermal throttle
curl -s 'localhost:9101/fault?xid=79&gpu=5'        # XID 79: GPU fell off the bus
curl -s 'localhost:9101/fault?quota=0.97'          # quota 97% full
curl -s 'localhost:9101/fault?link=rail2&up=0'     # back-end link down
sleep 40
curl -s localhost:9090/api/v1/alerts | python3 -c "import sys,json;[print(a['labels']['alertname'],a['state'],a['annotations']['summary']) for a in json.load(sys.stdin)['data']['alerts']]"
```
Expected (checked on my VM):
```
GPUThermalThrottle firing GPU 3 on xe-node-01 is throttling
GPUXidError firing XID 79 on GPU 5 (xe-node-01): drain node
StorageQuotaNearlyFull firing /ifs/ai/team-a quota 97% used
FabricLinkDown firing leaf1 rail2 down
```
Then stop the mockup (`docker compose --profile infra stop redfish`) and wait 45 s: `BMCUnreachable` fires. Start it again.
```bash
curl -s 'localhost:9101/fault?reset=1'; sleep 35; curl -s localhost:9090/api/v1/alerts   # alerts list empty
```

### Step 4 - Write the runbooks
Every rule in `prometheus/alerts.yml` has a `runbook` annotation. Write each runbook (one page): what the alert means, first checks, the automated action if any (`OPS-08`: e.g. cordon and drain the node on XID 79/48, requeue the job from its last checkpoint - BCR-07), escalation team, and the Dell support path (SupportAssist case, `OPS-06`).

### Step 5 - [HW/DEMO] Real sources
1. iDRAC: enable telemetry reports (C01 Step 7) and scrape them with the iDRAC Telemetry Reference Tools or a Redfish exporter.
2. GPUs: add the `nvidia-dcgm-exporter` service from C04 as a target. The simulated metric names match the real DCGM names, so the alert rules carry over.
3. PowerScale: InsightIQ or the OneFS exporter for capacity, latency and quota usage (map to `storage_quota_used_ratio`).
4. Switches: gNMI/streaming telemetry for interface state, PFC and ECN counters.
5. APEX AIOps: onboard the systems, record health score, the capacity forecast date, and which alerts it raises that your own stack did not.

### Step 6 - Decide the mandatory telemetry list
Table: metric, source, scrape interval, retention, alert threshold, owner. Cover GPU (util, memory, temp, power, XID, ECC), node (power, temp, fans, PSU), storage (capacity, latency, quota), fabric (link state, errors, PFC/ECN), scheduler (queue wait from C05).

## Verify
- [ ] Dashboard shows GPU, storage and fabric health on one page.
- [ ] Each injected fault fires its alert and clears after reset.
- [ ] A runbook exists for each alert.
- [ ] The mandatory telemetry list is written.

## Record for the standards
`OPS-03` mandatory GPU/fabric/storage telemetry. `OPS-01` observability stack. `OPS-02` Dell management tools (APEX AIOps, OME, InsightIQ). `OPS-08` automated remediation. `OPS-04` platform SLOs to publish.

## Cleanup
```bash
curl -s 'localhost:9101/fault?reset=1'
docker compose --profile infra --profile obs stop telemetry prometheus grafana
```
