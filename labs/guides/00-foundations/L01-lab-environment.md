# L01 - Build the lab environment

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (+ optional OneFS Simulator) | 4 h | PLT | L00 |

## What you build

| Lab component | Stands in for | Endpoint (host) | Compose profile |
|---|---|---|---|
| SeaweedFS S3 | ObjectScale (S3 API) | `http://localhost:8333` | core |
| Iceberg REST catalog | Lakehouse catalog | `http://localhost:8181` | core |
| Trino 476 | Data Analytics Engine (Starburst/Trino) | `http://localhost:8080` | core |
| PostgreSQL 16 (`crm.customers`) | Operational source system | `localhost:5432` | core |
| Elasticsearch 8.15 | Data Search Engine | `http://localhost:9200` | core |
| Apache Spark 3.5 + Iceberg | Data Processing Engine | `bin/spark-sql` | spark |
| DMTF Redfish Mockup Server | iDRAC Redfish API | `http://localhost:8000` | infra |
| Ollama (CPU) | NIM / LLM + embedding endpoint (OpenAI-compatible) | `http://localhost:11434` | ai |
| MLflow 2.22 | Model registry / tracking | `http://localhost:5000` | ai |
| Prometheus + Grafana | Observability / AIOps | `:9090`, `:3000` | obs |
| kind (3 nodes) | Kubernetes / OpenShift | `kubectl --context kind-aifactory-lab` | n/a |
| PowerScale OneFS Simulator *(optional)* | PowerScale | `$PS` | n/a (VM) |

## Prerequisites
- Linux or macOS host (or WSL2) with **8 vCPU / 16 GB RAM / 60 GB disk**. Add 8 GB if you also run the OneFS Simulator.
- Docker Engine 24+ with the Compose plugin, `git`, `make`, `curl`, `python3` (3.10+).
- For the Kubernetes labs: `kind` 0.29+, `kubectl`, `helm` 3.
- For PowerScale labs: a hypervisor that runs the OneFS Simulator, e.g. VMware Workstation / Fusion / ESXi, and a Dell Support account to download it.

## Steps

### Step 1 - Clone and configure
```bash
git clone https://github.com/lalith-chennupati/dataplatform.git
cd dataplatform/labs/env
cp .env.example .env          # change the passwords if the host is shared
```
`.env` sets `REGISTRY=mirror.gcr.io` (a Docker Hub mirror that avoids Hub rate limits) and `MAVEN_MIRROR` (Google's Maven Central mirror, used by Spark to fetch Iceberg jars). If you have direct Docker Hub access, set `REGISTRY=docker.io`.

### Step 2 - Start the core engines
```bash
make up                       # = docker compose --profile core up -d
docker compose --profile core ps
```
Expected: `s3`, `postgres`, `iceberg-rest`, `trino` and `elasticsearch` are `Up` (healthy), and `s3-init` has `Exited (0)` after creating the buckets `warehouse bu-finance bu-research model-registry checkpoints documents`.

### Step 3 - Start the optional profiles you need
```bash
make up PROFILES="core spark"           # Track B
make up PROFILES="core ai"              # Track D
make up PROFILES="core infra obs"       # Track C
make up-all                             # everything (~10 GB RAM)
```
For Track D, pull the CPU models once:
```bash
docker compose exec ollama ollama pull qwen2.5:0.5b        # small chat model
docker compose exec ollama ollama pull nomic-embed-text    # 768-dim embeddings
```

### Step 4 - Run the smoke test
```bash
make smoke
```
Expected (abridged):
```
core:
  PASS S3 endpoint lists buckets
  PASS tenant 'finance' writes its own bucket
  PASS cross-tenant write denied
  PASS Trino -> PostgreSQL federation
  PASS Trino -> Iceberg REST -> S3
  PASS Elasticsearch healthy
spark:
  PASS Spark reads the Iceberg table Trino wrote
...
all checks passed
```

### Step 5 - Create the Kubernetes cluster
```bash
make kind-up
kubectl get nodes -L pool
```
Expected: one control-plane and two workers labelled `pool=cpu` and `pool=gpu-sim`.

### Step 6 - [SIM, optional] Deploy the PowerScale OneFS Simulator
1. Download the **PowerScale OneFS Simulator** from Dell Support (search "OneFS Simulator"; free with a Dell Support account). Use a OneFS 9.x build.
2. Import the OVA into your hypervisor **three times** (a 3-node cluster is the minimum for most features). Give each VM 2 vCPU, 6 GB RAM and two NICs: *int-a* on an isolated host-only network, *ext-1* on a network your Docker host can reach.
3. Open the console of node 1 and run the configuration wizard: **Create a new cluster** -> set root/admin passwords -> cluster name `ps-lab` -> internal network `int-a` 192.168.100.0/24 -> external subnet, e.g. 10.10.10.0/24 with a range of 3 node IPs -> SmartConnect service IP, e.g. 10.10.10.50 -> DNS -> date/time -> commit.
4. On nodes 2 and 3, choose **Join an existing cluster** and pick `ps-lab`.
5. From your workstation:
   ```bash
   export PS=10.10.10.51           # any node IP
   ssh root@$PS isi status
   ssh root@$PS isi version
   ```
   Expected: `isi status` shows 3 healthy nodes.
6. Licences: features such as SmartQuotas, SnapshotIQ, SyncIQ, SmartLock, SmartPools and CloudPools need a licence. `isi license list` shows their status. The simulator normally runs licensed features in evaluation mode. If any show *Unlicensed*, ask your Dell team for an evaluation licence or note it in the evidence log.
7. For SyncIQ (A03, E04), build a **second** 1- or 3-node simulator cluster `ps-dr` the same way.

### Step 7 - Install the automation tooling
```bash
python3 -m venv ~/.venvs/aif && . ~/.venvs/aif/bin/activate
pip install ansible-core boto3 requests elasticsearch==8.15.1 mlflow==2.22.0 scikit-learn
ansible-galaxy collection install dellemc.powerscale dellemc.openmanage
# Terraform 1.6+ from https://developer.hashicorp.com/terraform/install for A05
```

### Step 8 - Record versions
```bash
docker compose --profile core --profile spark --profile ai ps --format '{{.Service}} {{.Image}}' > ../evidence/L01-versions.txt 2>/dev/null || true
ssh root@$PS isi version >> ../evidence/L01-versions.txt   # if the simulator is deployed
```

## Verify
- [ ] `make smoke` prints `all checks passed`.
- [ ] `kubectl get nodes` shows 3 Ready nodes.
- [ ] *(optional)* `ssh root@$PS isi status` shows a healthy 3-node cluster.
- [ ] `make destroy && make up && make smoke` rebuilds the lab from scratch.

## Record for the standards
`PLT-04` (provisioning toolchain): note what was easy or hard to automate. `PLT-09` (environments): the lab is your "sandbox" tier.

## Cleanup
```bash
make down        # keep data
make destroy     # delete data volumes too
make kind-down
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| `429 Too Many Requests` pulling images | Keep `REGISTRY=mirror.gcr.io`. Pull images one at a time and retry after a minute. |
| Spark: `unresolved dependency ... iceberg-spark-runtime` | Maven Central rate limit. Keep `MAVEN_MIRROR` set to the Google mirror in `.env`. |
| `s3` unhealthy | `docker compose logs s3`. The health check calls `http://127.0.0.1:8333/healthz` inside the container. |
| Elasticsearch exits with code 137 | Not enough RAM. Lower `ES_JAVA_OPTS` to `-Xms512m -Xmx512m`. |
| AWS SDK errors about checksums against the lab S3 | Keep `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` and `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required`. `bin/s3` sets them already. |
