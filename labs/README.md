# Dell AI Factory & Dell AI Data Platform (AIDP) - Lab Catalog

This catalog lists hands-on labs that cover the features of the **Dell AI Factory** (compute, fabric, AI software, services) and the **Dell AI Data Platform** (storage engines and data engines). Each lab lists:

- the Dell features it exercises,
- the environment it needs (see [Environment tiers](#environment-tiers)),
- its prerequisites, duration and success criteria,
- the questionnaire domains it informs (`questionnaire/questions.yaml` codes such as `STO`, `MLO`), so that lab findings feed back into the enterprise standards.

> **Naming caveat.** Product and feature names come from Dell's public portfolio as it stood when this catalog was written. Dell renames and re-bundles AIDP components often. For example, the Data Analytics Engine is Starburst/Trino based, the Data Processing Engine is Spark based and the Data Search Engine is Elastic based. Check names, versions and feature availability with your Dell account team or the Dell Demo Center before you build a lab.

## Environment tiers

| Tier | Meaning | Typical options |
|---|---|---|
| **SIM** | Runs on a laptop / VM / small Kubernetes cluster without Dell hardware. Uses a Dell simulator, a Dell open-source tool, or an open-source stand-in for the same engine. | PowerScale OneFS Simulator (virtual nodes), DMTF Redfish Mockup Server (iDRAC API shape), open-source Trino / Spark / Elasticsearch, MinIO as an S3 stand-in for ObjectScale, MicroK8s or kind, Dell Ansible collections / Terraform providers in check mode |
| **DEMO** | Needs a Dell-hosted environment: Dell Demo Center hands-on labs, a Dell Customer Solution Center engagement, or a time-boxed trial / partner lab. | democenter.dell.com interactive labs, Dell Customer Solution Centers, partner PoC labs |
| **HW** | Needs real Dell hardware and/or GPUs: PowerEdge XE / R-series GPU nodes, PowerScale / ObjectScale appliances, PowerSwitch or NVIDIA Spectrum-X / InfiniBand fabric. | Customer PoC rack, Dell AI Factory pilot, Dell APEX / as-a-service environment |

Many labs list more than one tier, e.g. `SIM / HW`. In those labs the SIM tier teaches the workflow and the APIs, and the HW tier is needed for the performance and accelerator steps.

## Learning path

```
L00 Orientation ─► L01 Lab environment
        │
        ├─► Track A  Storage engines (PowerScale, ObjectScale)        A01─A10
        ├─► Track B  Data engines (Lakehouse, Spark, Search)          B01─B07
        ├─► Track C  Compute, fabric & infrastructure automation      C01─C08
        ├─► Track D  AI software & workloads (NIM, RAG, tuning, agents) D01─D09
        └─► Track E  Security, resilience, operations & FinOps        E01─E06
                                   │
                                   ▼
                         X01 Capstone: standards-compliant AI Factory tenant
```

Suggested order for a first pass: L00 → L01 → A01 → A09 → B01 → B02 → D01 → D03 → C04 → E01 → X01.

## Lab summary

| ID | Lab | Key Dell features | Tier | Time | Domains |
|---|---|---|---|---|---|
| L00 | AI Factory & AIDP architecture orientation | Dell AI Factory reference designs, AIDP storage/data engine split | Paper | 2h | STR, ARC |
| L01 | Build the lab environment | OneFS Simulator, Kubernetes, OSS engine stand-ins | SIM | 4h | PLT |
| **Track A - Storage engines** | | | | | |
| A01 | PowerScale OneFS fundamentals | Cluster, SmartConnect, NFS/SMB/S3/HDFS multiprotocol | SIM | 3h | STO |
| A02 | Multi-tenancy with access zones & quotas | Access zones, SmartQuotas, OneFS RBAC, AD/LDAP providers | SIM | 3h | STO, SEC, FIN |
| A03 | Snapshots, replication & WORM | SnapshotIQ, SyncIQ, SmartLock | SIM | 3h | STO, BCR |
| A04 | Tiering hot -> cold | SmartPools, file pool policies, CloudPools to S3 | SIM / HW | 3h | STO, FIN |
| A05 | PowerScale automation as code | OneFS REST API (PAPI), Ansible `dellemc.powerscale`, Terraform `dell/powerscale` | SIM | 3h | PLT, ARC |
| A06 | PowerScale for Kubernetes AI jobs | CSI PowerScale, Container Storage Modules (Authorization, Observability, Replication) | SIM | 4h | STO, PLT |
| A07 | High-performance AI data path | NFS over RDMA, nconnect, NVIDIA GPUDirect Storage | HW | 4h | STO, CMP, NET |
| A08 | Discover AI-ready data with metadata | PowerScale MetadataIQ, file metadata indexing to search | DEMO / HW | 3h | DAT, STO |
| A09 | ObjectScale S3 fundamentals | Buckets, IAM users/policies, versioning, object lock, lifecycle | DEMO / SIM* | 3h | STO, SEC |
| A10 | S3 for AI workloads | Checkpoints and model artefacts on ObjectScale, multipart tuning, S3 over RDMA (where available) | SIM / HW | 3h | STO, MLO |
| **Track B - Data engines** | | | | | |
| B01 | Federated SQL with the Data Analytics Engine | Starburst/Trino connectors, federation across RDBMS + S3 + PowerScale | SIM / DEMO | 3h | LAK |
| B02 | Iceberg lakehouse on ObjectScale | Apache Iceberg tables, catalog, time travel, schema evolution, compaction | SIM | 4h | LAK, DAT |
| B03 | Lakehouse governance | Role-based access, row filters, column masks, audit (Starburst built-in access control) | DEMO / SIM | 3h | LAK, SEC, PRV |
| B04 | Data prep with the Data Processing Engine | Spark on Kubernetes, bronze/silver/gold pipelines, optional GPU (RAPIDS) | SIM / HW | 4h | ING, LAK |
| B05 | AI-assisted analytics | Natural-language-to-SQL, AI SQL functions, MCP access to the analytics engine | DEMO | 2h | LAK, AGT |
| B06 | Unstructured search with the Data Search Engine | Elastic-based ingestion of PowerScale content, hybrid keyword + vector search, document-level security | SIM / DEMO | 4h | RAG, SEC |
| B07 | GPU-accelerated vector indexing | NVIDIA cuVS / GPU index build vs. CPU baseline | HW | 3h | RAG, CMP |
| **Track C - Compute, fabric & infrastructure** | | | | | |
| C01 | PowerEdge lifecycle with iDRAC & Redfish | iDRAC Redfish API, inventory, firmware, telemetry streaming, secure boot, lockdown mode | SIM / HW | 3h | CMP, SEC |
| C02 | Fleet management with OpenManage Enterprise | Discovery, deployment templates, firmware baselines, compliance, Ansible `dellemc.openmanage` | DEMO / HW | 3h | OPS, PLT |
| C03 | Bare-metal AI cluster with Omnia | Dell Omnia provisioning of Kubernetes / Slurm, GPU drivers, node groups | SIM (VMs) / HW | 6h | PLT, CMP |
| C04 | GPUs on Kubernetes | NVIDIA GPU Operator, MIG, time-slicing, DCGM exporter on PowerEdge XE | HW | 4h | CMP, PLT |
| C05 | GPU scheduling, quotas & fair share | Kueue or Run:ai queues, Slurm partitions, pre-emption | SIM / HW | 3h | CMP, FIN |
| C06 | AI network fabric | Rail-optimised design, RoCE QoS (PFC/ECN), Dell Enterprise SONiC / Spectrum-X configuration, NCCL tests | SIM (SONiC VS) / HW | 4h | NET |
| C07 | Rack-scale & facilities readiness | Dell Integrated Rack Scalable Systems, power/cooling (DLC) sizing, site checklist | Paper / DEMO | 2h | FAC |
| C08 | Infrastructure telemetry & AIOps | iDRAC telemetry, DCGM, OneFS metrics, APEX AIOps (CloudIQ) health and capacity | SIM / DEMO | 3h | OPS |
| **Track D - AI software & workloads** | | | | | |
| D01 | Serve an LLM with NVIDIA NIM | NVIDIA AI Enterprise, NIM on Kubernetes, OpenAI-compatible API, model cache on PowerScale | HW (API-only: SIM) | 3h | MLO, PLT |
| D02 | Dell Enterprise Hub on Hugging Face | Dell-optimised model containers, deploy on PowerEdge, compare with NIM | HW | 3h | MLO |
| D03 | End-to-end RAG on the AI Data Platform | PowerScale docs -> Data Search Engine / vector index -> NIM LLM -> citations | SIM / HW | 6h | RAG, MLO |
| D04 | Fine-tune a model (LoRA) | NVIDIA NeMo or open-source PEFT, datasets on PowerScale, checkpoints on ObjectScale | HW | 6h | MLO, STO |
| D05 | Guardrails & evaluation | NeMo Guardrails, RAG evaluation (groundedness, relevance), red-team prompts | SIM / HW | 4h | MLO, SEC, GOV |
| D06 | Agentic AI on enterprise data | NVIDIA AI Blueprints (e.g. AI-Q / RAG blueprint), MCP tools over analytics + search engines | SIM / HW | 6h | AGT |
| D07 | MLOps pipeline | MLflow registry with artefacts on ObjectScale, KServe / NIM deploy, GitOps promotion | SIM | 5h | MLO, PLT |
| D08 | Red Hat OpenShift AI on Dell (optional) | OpenShift AI workbenches, model serving, CSI PowerScale | DEMO / HW | 5h | PLT, MLO |
| D09 | AI PC and edge inference (optional) | Dell Pro AI Studio, on-device models, edge-to-core data sync | HW (AI PC) | 3h | CMP, ARC |
| **Track E - Security, resilience, operations & FinOps** | | | | | |
| E01 | Zero-trust security baseline | OneFS RBAC + AD, TLS everywhere, S3 IAM, CSM Authorization, Kubernetes RBAC, secrets | SIM | 4h | SEC |
| E02 | Ransomware & cyber recovery | SmartLock, snapshot immutability, PowerScale cyber protection, PowerProtect Cyber Recovery vault | DEMO / HW | 4h | BCR, SEC |
| E03 | Backup & restore of AI assets | PowerProtect Data Manager for Kubernetes namespaces, model weights, vector indexes | DEMO / HW | 3h | BCR |
| E04 | DR drill for an AI service | SyncIQ failover/failback, re-deploy inference + RAG at DR site, RPO/RTO measurement | SIM / HW | 4h | BCR, OPS |
| E05 | Chargeback & capacity | Quota reports, GPU-hour metering, mandatory labels, showback dashboard | SIM | 3h | FIN |
| E06 | AI governance evidence | Model inventory, model cards, lineage, audit-log export for compliance | SIM | 3h | GOV, PRV |
| **Capstone** | | | | | |
| X01 | Standards-compliant AI Factory tenant | Onboard a tenant end-to-end against STD-01..STD-20 | SIM / HW | 1-2 days | All |

\* ObjectScale availability for self-hosted SIM varies. Use the Dell Demo Center or a trial if you can. Otherwise, run the S3 API steps against an S3-compatible stand-in (e.g. MinIO) and list which ObjectScale-specific features were not tested.

---

## L00 - AI Factory & AIDP architecture orientation

- **Objective:** Explain the layers of the Dell AI Factory and where the AI Data Platform fits.
- **Covers:** Dell AI Factory with NVIDIA / AMD / Intel variants. Infrastructure (PowerEdge, PowerSwitch, PowerScale, ObjectScale). AIDP's split between *storage engines* (PowerScale, ObjectScale) and *data engines* (Analytics, Processing, Search). The AI software stack (NVIDIA AI Enterprise, Dell Enterprise Hub). Services (Professional Services, ProSupport, APEX).
- **Activities:** Map the current enterprise estate onto the AI Factory layers. Mark gaps. Pick the target reference architecture. Draft answers to the `STR` and `ARC` P1 questions.
- **Done when:** A one-page layer diagram with owners and gaps exists, and `ARC-01` is answered.

## L01 - Build the lab environment

- **Objective:** Stand up a repeatable lab for the SIM-tier labs.
- **Covers:** PowerScale OneFS Simulator (3-node virtual cluster on a hypervisor). A Kubernetes cluster (MicroK8s / kind / OpenShift Local). Open-source stand-ins: Trino, Spark, Elasticsearch, an S3 endpoint. Dell Ansible collections and Terraform providers.
- **Activities:** Deploy the OneFS Simulator and join it to a lab AD/LDAP. Deploy Kubernetes with an ingress and cert-manager. Deploy the engine stand-ins with Helm. Install `dellemc.powerscale` and `dellemc.openmanage`. Write a `make up` / `make down` script.
- **Done when:** All endpoints answer health checks, and one script rebuilds the lab from scratch.

## Track A - Storage engines

### A01 - PowerScale OneFS fundamentals
- **Covers:** OneFS single namespace (`/ifs`), node pools, SmartConnect DNS load balancing, multiprotocol access (NFS, SMB, S3, HDFS) to the same files.
- **Activities:** Create a SmartConnect zone. Export one directory over NFS, SMB and S3. Write a file over NFS, read it over S3, and check permissions under each protocol.
- **Done when:** One dataset is readable over three protocols, and the ACL/permission behaviour per protocol is written down.

### A02 - Multi-tenancy with access zones & quotas
- **Covers:** Access zones, per-zone authentication providers, SmartQuotas (hard/soft/advisory), OneFS RBAC roles.
- **Activities:** Create one access zone per tenant (e.g. `bu-finance`, `bu-research`). Bind a different auth provider to each. Apply directory quotas. Delegate a zone-admin role. Exceed a soft quota and check the notification.
- **Done when:** Neither tenant can see the other's data, quota events fire, and the result answers the tenant-isolation model questions (`STO-06`, `STO-07`).

### A03 - Snapshots, replication & WORM
- **Covers:** SnapshotIQ schedules, SyncIQ replication policies (needs two simulator clusters), SmartLock compliance/enterprise mode.
- **Activities:** Schedule snapshots for a training-data directory. Replicate it to a second cluster. Put a curated "golden" training set in a SmartLock domain and try to delete it.
- **Done when:** A restore from snapshot works, the replica is consistent, the WORM delete is refused, and RPO is measured.

### A04 - Tiering hot -> cold
- **Covers:** SmartPools tiers, file pool policies (by age, path, type), CloudPools to an S3 target (ObjectScale or stand-in).
- **Activities:** Define hot and archive tiers. Write a policy that moves checkpoints older than N days. Run the SmartPools job and recall a stubbed file.
- **Done when:** The policy moves the data, recall works, and the capacity saved is recorded for `FIN`.

### A05 - PowerScale automation as code
- **Covers:** OneFS Platform API (PAPI) / REST, the Ansible `dellemc.powerscale` collection, the Terraform `dell/powerscale` provider.
- **Activities:** Write a playbook and Terraform plan that create an access zone, an NFS export, an S3 bucket and a quota from one tenant YAML. Run them twice to prove idempotence. Detect drift after a manual change.
- **Done when:** A tenant comes up from code in under 5 minutes and drift is reported.

### A06 - PowerScale for Kubernetes AI jobs
- **Covers:** The CSI PowerScale driver, StorageClasses, ReadWriteMany volumes, volume snapshots, Container Storage Modules (Authorization for tenant limits, Observability metrics, Replication).
- **Activities:** Install CSI PowerScale with Helm or the CSM Operator. Give a multi-pod PyTorch DataLoader job an RWX PVC. Snapshot the PVC. Enforce a per-namespace capacity limit with CSM Authorization.
- **Done when:** The job reads a shared dataset from 4+ pods, the snapshot restores, and the namespace limit is enforced.

### A07 - High-performance AI data path *(HW)*
- **Covers:** NFS over RDMA, `nconnect`, multipath client, NVIDIA GPUDirect Storage (GDS) on PowerEdge XE + PowerScale all-flash.
- **Activities:** Baseline TCP NFS with `fio`. Switch to NFSoRDMA. Run `gdsio` with GDS enabled and disabled. Measure checkpoint write time for a large model.
- **Done when:** A throughput/latency table per path exists and per-GPU throughput targets are set (`STO-04`).

### A08 - Discover AI-ready data with metadata
- **Covers:** PowerScale MetadataIQ (metadata indexing of OneFS into a search engine), custom tags, finding datasets by owner/age/type.
- **Activities:** Index a OneFS namespace. Query for "all PDFs owned by BU X changed in the last 90 days". Hand the result list to the D03 RAG ingestion.
- **Done when:** Data discovery is query-driven, not manual.

### A09 - ObjectScale S3 fundamentals
- **Covers:** Accounts/namespaces, buckets, IAM users, groups and policies, bucket policies, versioning, object lock (governance/compliance), lifecycle rules, encryption.
- **Activities:** Create a bucket per tenant with least-privilege policies. Enable versioning and object lock on a `model-registry` bucket. Add a lifecycle rule that expires temporary checkpoints.
- **Done when:** A cross-tenant access attempt is denied, a locked object cannot be deleted, and the lifecycle rule runs.

### A10 - S3 for AI workloads
- **Covers:** Model artefacts and checkpoints on ObjectScale, multipart upload tuning, an S3 data loader for PyTorch, S3 over RDMA where the platform supports it.
- **Activities:** Train a small model that checkpoints to S3. Compare multipart sizes and concurrency. Optionally compare S3 over RDMA with TCP on hardware.
- **Done when:** Checkpoint save/restore times are recorded and the bucket/prefix convention for artefacts is agreed.

## Track B - Data engines

### B01 - Federated SQL with the Data Analytics Engine
- **Covers:** The Starburst/Trino-based Data Analytics Engine, catalogs and connectors (PostgreSQL, Hive/Iceberg on S3, files on PowerScale), cost-based optimiser, query federation.
- **Activities:** Join a PostgreSQL customer table with Iceberg sales data in place, without copying it. Compare against an ETL copy.
- **Done when:** The federated query is correct, and the rule for choosing federation vs. ingestion is written for `LAK-04`.

### B02 - Iceberg lakehouse on ObjectScale
- **Covers:** Apache Iceberg tables, REST/Hive catalog, partitioning, time travel, schema evolution, snapshot expiry and compaction.
- **Activities:** Build raw -> curated -> consumption zones as Iceberg tables. Evolve a schema. Query `FOR VERSION AS OF`. Run compaction and snapshot expiry.
- **Done when:** The zone model and table-format standard (`LAK-02`, `LAK-05`) are proven.

### B03 - Lakehouse governance
- **Covers:** Role-based access control, row filters, column masking, query audit logs. Starburst built-in access control in the Dell edition, or an open-source equivalent (file-based rules / OPA) as a stand-in.
- **Activities:** Mask PII columns for analysts. Filter rows by region. Export the audit log for one query.
- **Done when:** The same query returns different results per role, and an audit record exists.

### B04 - Data prep with the Data Processing Engine
- **Covers:** The Spark-based Data Processing Engine, Spark on Kubernetes, Iceberg writes, optional RAPIDS Accelerator on GPU nodes.
- **Activities:** Write a bronze -> silver -> gold pipeline over PowerScale/ObjectScale data, scheduled by Airflow or Argo. On HW, compare CPU vs. GPU runtime.
- **Done when:** The pipeline is idempotent, data-quality checks run, and runtime/cost are recorded.

### B05 - AI-assisted analytics
- **Covers:** The analytics engine's AI features where available: natural-language-to-SQL, AI SQL functions (summarise, classify, embed), and MCP/agent access to governed data.
- **Activities:** Ask business questions in natural language and check the generated SQL. Call an LLM from SQL to classify support tickets. Expose a governed catalog to an agent over MCP.
- **Done when:** Generated SQL respects the B03 access controls.

### B06 - Unstructured search with the Data Search Engine
- **Covers:** The Elastic-based Data Search Engine, ingestion connectors for PowerScale content, chunking, embeddings, hybrid BM25 + vector search, re-ranking, document-level security.
- **Activities:** Ingest a PowerScale document share. Configure hybrid search. Check that a user without file ACL access gets no hits from restricted documents.
- **Done when:** Permission-aware retrieval is proven (`RAG-03`) and relevance is measured on a test set.

### B07 - GPU-accelerated vector indexing *(HW)*
- **Covers:** NVIDIA cuVS (CAGRA / IVF-PQ) GPU index building vs. a CPU HNSW baseline.
- **Activities:** Build indexes over 10M+ vectors on CPU and GPU. Compare build time, recall@10 and QPS.
- **Done when:** A sizing note for index tiers (`RAG-06`) exists.

## Track C - Compute, fabric & infrastructure

### C01 - PowerEdge lifecycle with iDRAC & Redfish
- **Covers:** iDRAC Redfish API, hardware inventory, firmware update, Server Configuration Profiles, telemetry streaming, secure boot, system lockdown mode.
- **Activities:** Pull GPU/CPU/NIC inventory with Redfish. Export and apply a Server Configuration Profile. Subscribe to telemetry reports. Enable lockdown mode. (SIM: run the API workflow against the DMTF Redfish Mockup Server. HW: real iDRAC.)
- **Done when:** Server baseline configuration is automated and the hardware security baseline (`SEC-12`) is checked.

### C02 - Fleet management with OpenManage Enterprise
- **Covers:** OpenManage Enterprise discovery, groups, deployment templates, firmware/driver catalogs and baselines, compliance reports, alert policies, Ansible `dellemc.openmanage`.
- **Activities:** Discover GPU nodes. Create a firmware baseline from the validated AI Factory matrix. Report non-compliant nodes and fix them with Ansible.
- **Done when:** A fleet compliance report exists for the driver/firmware matrix (`PLT-03`).

### C03 - Bare-metal AI cluster with Omnia
- **Covers:** Dell Omnia (open source): PXE provisioning, OS deployment, Kubernetes and/or Slurm, NVIDIA/AMD GPU drivers, InfiniBand/RoCE setup, node groups.
- **Activities:** Provision a control node and 2+ compute nodes (VMs for SIM, PowerEdge for HW). Deploy Kubernetes and Slurm. Add a node and check that it joins cleanly.
- **Done when:** A rebuild from bare metal is repeatable and the provisioning toolchain (`PLT-04`) is chosen.

### C04 - GPUs on Kubernetes *(HW)*
- **Covers:** NVIDIA GPU Operator, MIG profiles, time-slicing, DCGM exporter, node feature discovery on PowerEdge XE GPU nodes.
- **Activities:** Install the GPU Operator. Partition an H100/H200/B200-class GPU with MIG. Run concurrent inference pods. Export DCGM metrics to Prometheus.
- **Done when:** The GPU sharing policy (`CMP-05`) is tested and utilisation is visible per namespace.

### C05 - GPU scheduling, quotas & fair share
- **Covers:** Kueue ClusterQueues/cohorts or NVIDIA Run:ai projects, Slurm partitions and QOS, priority and pre-emption.
- **Activities:** Create quotas for 3 teams. Submit more jobs than fit. Check borrowing, pre-emption and fair-share behaviour.
- **Done when:** The quota/pre-emption policy (`CMP-07`) is proven and the queue wait-time metric exists.

### C06 - AI network fabric
- **Covers:** Rail-optimised back-end design, RoCEv2 lossless config (PFC, ECN, DCQCN), Dell Enterprise SONiC on PowerSwitch or NVIDIA Spectrum-X / InfiniBand, BlueField SuperNIC/DPU, NCCL all-reduce tests.
- **Activities:** SIM: build the leaf/spine config on SONiC virtual switches and validate QoS config as code. HW: run `nccl-tests` all-reduce across nodes and compare bus bandwidth against the design target.
- **Done when:** Fabric config is in Git and NCCL bandwidth meets target (`NET-01`..`NET-04`).

### C07 - Rack-scale & facilities readiness
- **Covers:** Dell Integrated Rack Scalable Systems, rack power density (kW/rack), direct liquid cooling, site-readiness checklist.
- **Activities:** Size power and cooling for the target GPU count. Fill in the site-readiness checklist with facilities staff.
- **Done when:** `FAC-01`..`FAC-04` are answered with numbers.

### C08 - Infrastructure telemetry & AIOps
- **Covers:** iDRAC telemetry, DCGM, OneFS metrics (InsightIQ / exporters), switch telemetry, APEX AIOps (CloudIQ) health scores and capacity forecasts.
- **Activities:** Build one Grafana dashboard for GPU, storage and fabric health. Inject faults (fill a quota, throttle a GPU, flap a link) and confirm the alerts fire.
- **Done when:** The mandatory telemetry list (`OPS-03`) is implemented and alert runbooks exist.

## Track D - AI software & workloads

### D01 - Serve an LLM with NVIDIA NIM
- **Covers:** NVIDIA AI Enterprise licensing, NIM containers on Kubernetes (NIM Operator / Helm), OpenAI-compatible endpoints, model cache on a PowerScale RWX volume, autoscaling.
- **Activities:** Deploy an 8B-class NIM. Cache the weights on PowerScale. Load-test tokens/s and p95 latency. Scale replicas. (SIM: call the hosted API catalog endpoint to learn the API only.)
- **Done when:** Inference SLOs (`MLO-06`) are measured and the serving-runtime standard is chosen.

### D02 - Dell Enterprise Hub on Hugging Face *(HW)*
- **Covers:** Dell Enterprise Hub curated models and Dell-optimised containers, deployment on PowerEdge, comparison with D01.
- **Activities:** Deploy the same model family from Dell Enterprise Hub. Compare throughput, latency, footprint and operational effort with NIM.
- **Done when:** An approved model-source decision (`MLO-01`) exists.

### D03 - End-to-end RAG on the AI Data Platform
- **Covers:** Documents on PowerScale -> discovery (A08) -> parsing/chunking -> embeddings -> Data Search Engine or vector DB -> NIM LLM -> answers with citations. NVIDIA RAG blueprint as the reference.
- **Activities:** Build a RAG assistant over a department's documents. Enforce document ACLs from B06. Add incremental re-indexing and deletion propagation.
- **Done when:** Answers cite sources, restricted documents never leak, and the index refreshes within the agreed SLA.

### D04 - Fine-tune a model (LoRA) *(HW)*
- **Covers:** NVIDIA NeMo customisation (or open-source PEFT), dataset versioning on PowerScale, checkpointing to ObjectScale, multi-GPU training.
- **Activities:** LoRA-tune a model on a curated dataset. Checkpoint every N steps. Kill a worker and resume. Register the adapter.
- **Done when:** Resume from checkpoint works and the fine-tuning policy (`MLO-10`) and checkpoint policy (`BCR-07`) are validated.

### D05 - Guardrails & evaluation
- **Covers:** NeMo Guardrails (topic, jailbreak, PII rails), RAG evaluation (groundedness, answer relevance, context precision), red-team prompt suites mapped to the OWASP Top 10 for LLM Applications.
- **Activities:** Wrap the D03 assistant with guardrails. Run an evaluation and a red-team suite before and after. Set release thresholds.
- **Done when:** A pre-release evaluation gate (`MLO-07`) exists with pass/fail thresholds.

### D06 - Agentic AI on enterprise data
- **Covers:** NVIDIA AI Blueprints for agents/research assistants, MCP servers for the analytics engine (B05) and search engine (B06), tool registry, on-behalf-of identity, step-level tracing.
- **Activities:** Build an agent that answers "why did region X sales drop?" by combining SQL and document search. Log every tool call. Enforce read-only autonomy.
- **Done when:** The agent autonomy matrix and audit trail (`AGT-03`, `AGT-06`) are demonstrated.

### D07 - MLOps pipeline
- **Covers:** MLflow tracking and registry with artefacts on ObjectScale, CI that builds and scans images, KServe or NIM deployment, GitOps (Argo CD) promotion dev -> prod, canary and rollback.
- **Activities:** Train -> register -> approve -> deploy -> roll back a model, all through Git.
- **Done when:** A model promotion leaves a full audit trail and rollback takes under 5 minutes.

### D08 - Red Hat OpenShift AI on Dell *(optional)*
- **Covers:** OpenShift AI workbenches, data science pipelines, model serving, GPU operator, CSI PowerScale on OpenShift.
- **Activities:** Repeat D07 on OpenShift AI and compare the operator experience with upstream Kubernetes.
- **Done when:** The platform choice (`PLT-01`) is backed by evidence.

### D09 - AI PC and edge inference *(optional)*
- **Covers:** Dell Pro AI Studio and on-device (NPU/GPU) inference on Dell AI PCs, edge-to-core sync to PowerScale/ObjectScale.
- **Activities:** Run a small model locally. Sync feedback data back to the core platform under the data-classification rules.
- **Done when:** The client/edge AI standard (`CMP-11`) is drafted.

## Track E - Security, resilience, operations & FinOps

### E01 - Zero-trust security baseline
- **Covers:** OneFS RBAC and AD integration, TLS for all endpoints (cert-manager), S3 IAM least privilege, CSM Authorization, Kubernetes RBAC and NetworkPolicies, external secrets, image signing.
- **Activities:** Apply the baseline. Run a checklist scan. Try lateral moves between tenants and confirm each is blocked.
- **Done when:** Every `SEC` P1 question has a tested control.

### E02 - Ransomware & cyber recovery
- **Covers:** SmartLock and immutable snapshots, PowerScale cyber protection / ransomware detection options, PowerProtect Cyber Recovery isolated vault.
- **Activities:** Simulate mass encryption in a lab share. Detect it, restore from immutable copies, and time the recovery.
- **Done when:** A cyber-recovery runbook exists with measured recovery time.

### E03 - Backup & restore of AI assets
- **Covers:** PowerProtect Data Manager protection of Kubernetes namespaces, PVCs, model weights and vector indexes.
- **Activities:** Back up the D03 namespace. Delete it, restore it, and confirm the service works.
- **Done when:** The protection scope (`BCR-01`) is tested for every asset type.

### E04 - DR drill for an AI service
- **Covers:** SyncIQ failover/failback, GitOps re-deploy at the DR site, DNS cut-over.
- **Activities:** Fail the D03 RAG service over to the DR site. Measure RPO and RTO, then fail back.
- **Done when:** Measured RPO/RTO are compared with the targets in `BCR-02`.

### E05 - Chargeback & capacity
- **Covers:** SmartQuotas reports, ObjectScale bucket metering, GPU-hour metering from DCGM/scheduler, mandatory labels, showback dashboard.
- **Activities:** Generate a monthly showback per tenant (GPU-hours, TB-month, tokens). Flag unlabelled workloads.
- **Done when:** The rate card and tagging standard (`FIN-02`, `FIN-03`) work on real metrics.

### E06 - AI governance evidence
- **Covers:** AI inventory, model cards, data lineage across lakehouse -> features/embeddings -> model, audit-log export.
- **Activities:** Generate an evidence pack for one production use case that an auditor could review.
- **Done when:** The evidence pack satisfies `GOV-06`, `PRV-05`.

## X01 - Capstone: standards-compliant AI Factory tenant

- **Objective:** Onboard a new business-unit tenant end-to-end, following the standards that the questionnaire produced.
- **Activities:** From one tenant request, create the access zone/bucket/quota (A02, A05, A09), lakehouse catalog and policies (B02, B03), GPU queue (C05), a RAG assistant with guardrails (D03, D05), monitoring and chargeback (C08, E05), and backup/DR (E03, E04). Record every deviation from the standards as an exception.
- **Done when:** The tenant is live from code. Every STD-xx clause is satisfied or has an approved exception, and the lessons learned are fed back into `questionnaire/questions.yaml`.

## Coverage matrix

| Feature area | Labs |
|---|---|
| PowerScale (OneFS) | A01-A08, B06, D03, E02, E04 |
| ObjectScale | A09, A10, B02, D04, D07 |
| Data Analytics Engine (Starburst/Trino) | B01-B03, B05 |
| Data Processing Engine (Spark) | B04 |
| Data Search Engine (Elastic) / vector search | B06, B07, D03 |
| PowerEdge / iDRAC / OpenManage | C01, C02, C04 |
| Omnia & cluster provisioning | C03 |
| Network fabric (PowerSwitch / SONiC / Spectrum-X / InfiniBand) | C06, A07 |
| NVIDIA AI Enterprise (NIM, NeMo, Guardrails, Blueprints) | D01, D03-D06 |
| Dell Enterprise Hub on Hugging Face | D02 |
| Kubernetes / OpenShift / CSM | A06, C04, C05, D07, D08 |
| Observability & APEX AIOps | C08 |
| Security | E01, B03, B06, C01 |
| Backup, cyber recovery & DR | A03, E02-E04 |
| FinOps | A02, A04, C05, E05 |
| Governance & compliance | D05, E06, X01 |
| Facilities | C07 |
