# Dell AI Factory & AI Data Platform - Enterprise Standards Questionnaire

Version 1.0 - 186 questions across 20 domains (95 are P1).

> Generated from `questionnaire/questions.yaml` by `tools/build_questionnaire.py`. Do not edit by hand.

**Priority:** **P1** Needed before Day-0 platform build (architecture, procurement, security baseline) | **P2** Needed before the first production AI workload goes live | **P3** Needed within the first two quarters of operation (optimisation, scale-out)

**Roles:** `EXEC` Executive sponsor / AI steering committee, `EA` Enterprise / solution architect, `CDO` Chief Data Officer / data governance lead, `DE` Data engineering lead, `DS` Data science / ML engineering lead, `PLAT` Platform engineering / Kubernetes lead, `INFRA` Compute & storage infrastructure lead, `NET` Network engineering lead, `SEC` CISO / security architecture, `LEGAL` Legal, privacy & compliance, `OPS` IT operations / SRE, `FIN` Finance / FinOps, `FAC` Data center facilities, `HR` HR / learning & development, `PROC` Procurement / vendor management

## Domains

- [STR - Strategy, Business Alignment & Use Cases](#str---strategy-business-alignment--use-cases) -> STD-01 AI Strategy & Use-Case Intake Standard
- [GOV - AI Governance, Risk & Responsible AI](#gov---ai-governance-risk--responsible-ai) -> STD-02 AI Governance & Responsible AI Policy
- [DAT - Data Strategy, Governance & Lifecycle](#dat---data-strategy-governance--lifecycle) -> STD-03 Data Governance, Classification & Lifecycle Standard
- [STO - Storage Engines (PowerScale / ObjectScale)](#sto---storage-engines-powerscale--objectscale) -> STD-04 AI Storage Services Standard
- [LAK - Data Engines - Lakehouse, Processing & Analytics](#lak---data-engines---lakehouse-processing--analytics) -> STD-05 Lakehouse & Data Engine Standard
- [ING - Data Ingestion, Integration & Pipelines](#ing---data-ingestion-integration--pipelines) -> STD-06 Data Ingestion & Pipeline Standard
- [RAG - Retrieval, Vector Search & Knowledge (RAG)](#rag---retrieval-vector-search--knowledge-rag) -> STD-07 Retrieval-Augmented Generation & Vector Search Standard
- [CMP - Compute & Accelerators](#cmp---compute--accelerators) -> STD-08 AI Compute & Accelerator Standard
- [NET - Networking & Fabric](#net---networking--fabric) -> STD-09 AI Network Fabric Standard
- [PLT - Platform Software, Kubernetes & AI Software Stack](#plt---platform-software-kubernetes--ai-software-stack) -> STD-10 Platform Software & AI Stack Standard
- [MLO - Model Lifecycle - MLOps / LLMOps](#mlo---model-lifecycle---mlops--llmops) -> STD-11 Model Lifecycle (MLOps / LLMOps) Standard
- [AGT - Agentic AI & Tool Integration](#agt---agentic-ai--tool-integration) -> STD-12 Agentic AI Standard
- [SEC - Security, Identity & Zero Trust](#sec---security-identity--zero-trust) -> STD-13 AI Security & Identity Standard
- [PRV - Privacy & Regulatory Compliance](#prv---privacy--regulatory-compliance) -> STD-14 Privacy & Regulatory Compliance Standard
- [OPS - Operations, Observability & Support](#ops---operations-observability--support) -> STD-15 AI Operations & Observability Standard
- [BCR - Resilience, Backup & Cyber Recovery](#bcr---resilience-backup--cyber-recovery) -> STD-16 Resilience, Backup & Cyber Recovery Standard
- [FIN - FinOps, Chargeback & Capacity Management](#fin---finops-chargeback--capacity-management) -> STD-17 AI FinOps & Capacity Standard
- [FAC - Data Center Facilities & Sustainability](#fac---data-center-facilities--sustainability) -> STD-18 AI Data Center & Sustainability Standard
- [ORG - Operating Model, Skills & Adoption](#org---operating-model-skills--adoption) -> STD-19 AI Operating Model & Skills Standard
- [ARC - Architecture Standards, Interoperability & Vendor Strategy](#arc---architecture-standards-interoperability--vendor-strategy) -> STD-20 Reference Architecture, Naming & Exception Standard

## STR - Strategy, Business Alignment & Use Cases

**Target standard:** STD-01 AI Strategy & Use-Case Intake Standard  
**Intent:** Anchor every platform standard to business outcomes, a prioritised use-case portfolio and measurable value.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| STR-01 | What are the top 3-5 business outcomes the AI Factory must deliver in the next 12-24 months? | Free text | EXEC | P1 | Strategic objectives and success KPIs |
| STR-02 | Which AI workload classes are in scope? | Generative AI / LLM inference / RAG / enterprise search / Agentic AI / Model fine-tuning / Foundation model pre-training / Classical ML / Computer vision / Analytics / BI on lakehouse / Digital twins / simulation / Edge AI | EA | P1 | Workload classes the platform must support (sizing baseline) |
| STR-03 | Is there a documented, prioritised AI use-case backlog with business owners and value estimates? | Yes / No / Partial / Unknown | EXEC | P1 | Use-case intake and prioritisation process |
| STR-04 | How many AI use cases are expected in production at 6, 12 and 24 months? | Free text | EXEC | P1 | Capacity and onboarding throughput targets |
| STR-05 | What is the intended deployment model for the AI Factory? | On-premises data center / Colocation / Hybrid on-prem + public cloud / Edge + core / Dell APEX / as-a-service consumption / Undecided | EA | P1 | Deployment and consumption model |
| STR-06 | What criteria decide whether a workload runs on the on-prem AI Factory vs. public cloud AI services? | Free text | EA | P1 | Workload placement policy (data gravity, sovereignty, cost, latency) |
| STR-07 | What value metrics will be tracked per use case (e.g. hours saved, revenue, cost avoided, CSAT)? | Free text | FIN | P2 | Value realisation and benefits tracking |
| STR-08 | What is the stage-gate for moving a use case from idea -> PoC -> pilot -> production? | Free text | EXEC | P2 | Use-case lifecycle stage gates and exit criteria |
| STR-09 | Is there a build vs. buy vs. partner policy for AI capabilities (custom models, SaaS copilots, ISV solutions)? | Yes / No / Partial / Unknown | EA | P2 | Sourcing decision framework |
| STR-10 | Which business units are first adopters and who is the accountable business owner for each? | Free text | EXEC | P1 | Tenant onboarding order and accountability |

## GOV - AI Governance, Risk & Responsible AI

**Target standard:** STD-02 AI Governance & Responsible AI Policy  
**Intent:** Define who approves AI, how risk is classified, and which external frameworks the enterprise aligns to.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| GOV-01 | Is there a chartered AI governance body (AI council / steering committee) with decision rights? | Yes / No / Partial / Unknown | EXEC | P1 | Governance bodies, membership and decision rights |
| GOV-02 | Which external frameworks must the AI standards align to? | NIST AI RMF 1.0 / ISO/IEC 42001 / ISO/IEC 23894 / EU AI Act / OECD AI Principles / Industry regulator guidance / Internal only | LEGAL | P1 | Framework alignment and control mapping |
| GOV-03 | Is there an AI risk-tiering scheme (e.g. minimal / limited / high / prohibited) applied to every use case? | Yes / No / Partial / Unknown | LEGAL | P1 | AI risk classification and required controls per tier |
| GOV-04 | Which uses of AI are explicitly prohibited or require executive approval? | Free text | LEGAL | P1 | Prohibited / restricted use list |
| GOV-05 | Is a pre-deployment AI impact assessment (bias, safety, privacy, IP) mandatory? Who signs off? | Free text | LEGAL | P2 | AI impact assessment template and approvers |
| GOV-06 | Is there a central AI inventory / registry of all models, agents and AI-enabled applications? | Yes / No / Partial / Unknown | CDO | P2 | AI system inventory (mandatory registration fields) |
| GOV-07 | What human-in-the-loop / human-oversight requirements apply to AI decisions affecting customers or employees? | Free text | LEGAL | P2 | Human oversight requirements by risk tier |
| GOV-08 | What transparency requirements apply (disclosing AI-generated content, model cards, user notices)? | Free text | LEGAL | P2 | Transparency and disclosure rules |
| GOV-09 | How are fairness / bias metrics defined, measured and thresholded for high-risk models? | Free text | DS | P2 | Fairness evaluation and acceptance thresholds |
| GOV-10 | What is the policy on use of copyrighted, licensed or third-party data for training and fine-tuning? | Free text | LEGAL | P1 | Training-data IP and licensing rules |
| GOV-11 | How are AI incidents (harmful output, data leak, model failure) reported, triaged and disclosed? | Free text | SEC | P2 | AI incident management process |
| GOV-12 | How often are standards and policies reviewed, and what is the exception / waiver process? | Free text | EA | P2 | Policy review cadence and exception handling |

## DAT - Data Strategy, Governance & Lifecycle

**Target standard:** STD-03 Data Governance, Classification & Lifecycle Standard  
**Intent:** Make enterprise data AI-ready - classified, owned, catalogued, quality-assured and lifecycle-managed.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| DAT-01 | What is the enterprise data classification scheme and how many levels does it have? | Public / Internal / Confidential / Restricted / 3-level scheme / 5+ level scheme / No formal scheme | CDO | P1 | Classification levels and handling rules on the AI Data Platform |
| DAT-02 | Are data owners and data stewards assigned for the domains that will feed AI use cases? | Yes / No / Partial / Unknown | CDO | P1 | Data ownership and stewardship RACI |
| DAT-03 | Which data sources will feed the AI Factory initially (ERP, CRM, file shares, data warehouse, logs, IoT, documents, email)? | Free text | DE | P1 | Source system onboarding list |
| DAT-04 | What is the estimated data volume to land on the platform (TB/PB) at Day-0, 12 and 36 months, and its growth rate? | Free text | DE | P1 | Capacity baseline for storage engines |
| DAT-05 | What share of the data is unstructured (documents, images, video, audio) vs. structured / semi-structured? | Free text | DE | P1 | File vs. object vs. table storage split |
| DAT-06 | Is there an enterprise data catalog / metadata management tool in use? Which one? | Free text | CDO | P1 | Catalog of record and mandatory metadata fields |
| DAT-07 | Is end-to-end data lineage (source -> feature/embedding -> model -> output) required? | Yes / No / Partial / Unknown | CDO | P2 | Lineage capture requirements |
| DAT-08 | What data quality dimensions and thresholds must be met before data is used for training or RAG? | Free text | CDO | P2 | Data quality rules and gating |
| DAT-09 | Are retention, archival and legal-hold rules defined per data class, including for prompts, embeddings and model outputs? | Yes / No / Partial / Unknown | LEGAL | P2 | Retention schedule including AI artefacts |
| DAT-10 | Is synthetic data or data anonymisation / pseudonymisation used or planned? | Yes / No / Partial / Unknown | CDO | P3 | Synthetic and de-identified data rules |
| DAT-11 | Are data products / data contracts used between producing and consuming teams? | Yes / No / Partial / Unknown | DE | P3 | Data product and contract standard |
| DAT-12 | What is the data sovereignty / residency requirement (countries, regions, sites)? | Free text | LEGAL | P1 | Data residency and cross-border transfer rules |

## STO - Storage Engines (PowerScale / ObjectScale)

**Target standard:** STD-04 AI Storage Services Standard  
**Intent:** Standardise the storage service catalogue - file vs. object, performance tiers, tenancy, protection and data access protocols.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| STO-01 | Which storage engines are in scope? | Dell PowerScale (scale-out file / NAS) / Dell ObjectScale (S3 object) / Existing third-party NAS / Existing third-party object store / Public cloud object storage / Parallel file system | INFRA | P1 | Approved storage platforms |
| STO-02 | Which data access protocols must be supported? | NFSv3 / NFSv4.x / NFS over RDMA / SMB / S3 / S3 over RDMA / HDFS / POSIX parallel FS client | INFRA | P1 | Supported protocols per storage service |
| STO-03 | Is NVIDIA GPUDirect Storage (GDS) or RDMA data access required for training / high-throughput inference? | Yes / No / Partial / Unknown | INFRA | P1 | High-performance data path requirements |
| STO-04 | What throughput (GB/s) and IOPS targets are required per GPU node / per cluster for training and checkpointing? | Free text | INFRA | P1 | Performance tier definitions and SLOs |
| STO-05 | How should storage tiers be defined (e.g. all-flash hot, hybrid warm, archive / cloud tier) and what moves data between them? | Free text | INFRA | P2 | Tiering policy (e.g. SmartPools / CloudPools / lifecycle rules) |
| STO-06 | What multi-tenancy model is required (access zones, namespaces, buckets per team / per use case)? | Per business unit / Per project / use case / Per environment (dev/test/prod) / Shared with ACLs only / Undecided | INFRA | P1 | Tenant isolation model and naming |
| STO-07 | Are quotas and capacity guardrails required per tenant / project? | Yes / No / Partial / Unknown | INFRA | P2 | Quota standard (hard / soft / advisory) |
| STO-08 | What snapshot and replication RPO/RTO are required per data class? | Free text | INFRA | P2 | Snapshot and replication policy |
| STO-09 | Is immutability / WORM / object lock required for any data (regulatory, training-set provenance, audit)? | Yes / No / Partial / Unknown | LEGAL | P2 | Immutability and object-lock rules |
| STO-10 | Is metadata indexing / search over file and object metadata needed to discover AI-ready data? | Yes / No / Partial / Unknown | DE | P3 | Metadata indexing and tagging (e.g. PowerScale MetadataIQ) |
| STO-11 | Which Kubernetes CSI / Container Storage Modules integrations are required for containerised AI workloads? | Free text | PLAT | P2 | Persistent storage for Kubernetes (CSI drivers, storage classes) |
| STO-12 | What existing storage must be migrated or federated into the AI Data Platform and on what timeline? | Free text | INFRA | P1 | Migration / co-existence plan |

## LAK - Data Engines - Lakehouse, Processing & Analytics

**Target standard:** STD-05 Lakehouse & Data Engine Standard  
**Intent:** Standardise table formats, catalogs, query federation and processing engines that prepare data for AI.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| LAK-01 | Which data engines are in scope? | Dell Data Lakehouse / Data Analytics Engine (Trino / Starburst based) / Spark-based data processing engine / Existing enterprise data warehouse / Databricks / Snowflake / Cloud-native lakehouse / Undecided | EA | P1 | Approved data engines and their roles |
| LAK-02 | What is the standard open table format? | Apache Iceberg / Delta Lake / Apache Hudi / Multiple allowed / Undecided | DE | P1 | Table format standard |
| LAK-03 | Which metastore / catalog is the system of record for table metadata (e.g. Iceberg REST, Hive, Unity, Polaris)? | Free text | DE | P1 | Catalog of record for lakehouse tables |
| LAK-04 | Is federated query across existing databases and clouds required instead of copying data? | Yes / No / Partial / Unknown | DE | P2 | Federation vs. ingestion decision rules |
| LAK-05 | What zone / layer model will be used (e.g. raw / bronze -> curated / silver -> consumption / gold)? | Free text | DE | P1 | Lakehouse zone model and promotion rules |
| LAK-06 | What are the standard file formats and compression codecs for ingested data? | Free text | DE | P2 | File format and partitioning conventions |
| LAK-07 | Is GPU-accelerated data processing (e.g. RAPIDS / Spark on GPU) required for data prep? | Yes / No / Partial / Unknown | DE | P3 | Accelerated processing usage criteria |
| LAK-08 | Which BI / analytics tools must connect to the lakehouse? | Free text | DE | P2 | Supported consumer tools and connectors |
| LAK-09 | What fine-grained access controls (row / column masking, tag-based policies) are needed at the query layer? | Free text | SEC | P1 | Query-layer access control model |
| LAK-10 | Is a feature store required for classical ML, and should it be on the lakehouse? | Yes / No / Partial / Unknown | DS | P3 | Feature store standard |

## ING - Data Ingestion, Integration & Pipelines

**Target standard:** STD-06 Data Ingestion & Pipeline Standard  
**Intent:** Define how data gets onto the platform - batch, streaming, CDC, document ingestion - with orchestration and observability.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| ING-01 | Which ingestion patterns are required? | Batch file transfer / Database CDC / Streaming (Kafka / event hub) / API pull / Document / content repository crawl / IoT / edge sync / Manual upload | DE | P1 | Approved ingestion patterns |
| ING-02 | Which ingestion / ETL / ELT tools are already licensed and should be reused? | Free text | DE | P1 | Approved integration tooling |
| ING-03 | What orchestration tool is the standard (e.g. Airflow, Argo Workflows, Dagster, Control-M)? | Free text | DE | P2 | Pipeline orchestration standard |
| ING-04 | What freshness / latency SLAs do AI use cases need from source data? | Free text | DE | P2 | Data freshness SLA tiers |
| ING-05 | How should unstructured content (PDF, Office, HTML, scans) be parsed, chunked and enriched for AI? | Free text | DS | P2 | Document processing pipeline standard |
| ING-06 | Is pipeline code required to be version-controlled with CI/CD and automated tests? | Yes / No / Partial / Unknown | DE | P2 | Pipeline engineering practices |
| ING-07 | How are schema changes and breaking changes from sources detected and handled? | Free text | DE | P3 | Schema evolution policy |
| ING-08 | Is sensitive-data detection / redaction (PII, PHI, secrets) required during ingestion? | Yes / No / Partial / Unknown | SEC | P1 | Inline sensitive-data scanning |
| ING-09 | How should pipeline failures, data quality breaches and SLA misses be alerted and owned? | Free text | OPS | P2 | Pipeline observability and on-call |

## RAG - Retrieval, Vector Search & Knowledge (RAG)

**Target standard:** STD-07 Retrieval-Augmented Generation & Vector Search Standard  
**Intent:** Standardise embedding, indexing, retrieval and permission-aware search used by GenAI and agents.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| RAG-01 | Which vector / search engine(s) will be standard? | Dell Data Search Engine (Elastic-based) / Elasticsearch / OpenSearch / Milvus / pgvector / NVIDIA cuVS-accelerated index / Vendor-managed vector DB / Undecided | EA | P1 | Approved vector / search engines |
| RAG-02 | Is hybrid search (keyword + vector) and re-ranking required? | Yes / No / Partial / Unknown | DS | P2 | Retrieval pipeline reference design |
| RAG-03 | Must retrieval enforce source-system permissions (document-level ACLs) for every user query? | Yes / No / Partial / Unknown | SEC | P1 | Permission-aware retrieval requirement |
| RAG-04 | Which embedding models are approved, and how is embedding model versioning / re-indexing handled? | Free text | DS | P2 | Embedding model registry and re-index policy |
| RAG-05 | What chunking, metadata and citation standards must RAG applications follow? | Free text | DS | P2 | Chunking and citation rules |
| RAG-06 | What is the expected corpus size (documents / vectors) and query volume (QPS) per application? | Free text | DS | P1 | Index sizing and scaling tiers |
| RAG-07 | How is index freshness kept in sync with source changes and deletions (right-to-be-forgotten)? | Free text | DE | P2 | Index refresh and deletion propagation |
| RAG-08 | How are RAG answers evaluated for groundedness, relevance and hallucination before and after release? | Free text | DS | P2 | RAG evaluation metrics and thresholds |

## CMP - Compute & Accelerators

**Target standard:** STD-08 AI Compute & Accelerator Standard  
**Intent:** Standardise server SKUs, GPU classes, partitioning and scheduling for training, fine-tuning and inference.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| CMP-01 | Which accelerator ecosystems are approved? | NVIDIA / AMD Instinct / Intel Gaudi / CPU-only inference / Undecided | INFRA | P1 | Approved accelerator vendors |
| CMP-02 | Which PowerEdge server classes are anticipated (e.g. XE-series 8-GPU training nodes, PCIe GPU inference nodes, rack-scale systems)? | Free text | INFRA | P1 | Standard server building blocks (SKUs) |
| CMP-03 | What is the expected workload mix by GPU-hours: training / fine-tuning / inference / data prep? | Free text | DS | P1 | Cluster sizing and node-pool split |
| CMP-04 | What is the largest model (parameters) to be trained, fine-tuned or served, and with what context length? | Free text | DS | P1 | GPU memory and interconnect requirements |
| CMP-05 | Is GPU partitioning / sharing required (MIG, time-slicing, vGPU)? | Yes / No / Partial / Unknown | PLAT | P2 | GPU sharing policy |
| CMP-06 | Which workload scheduler(s) will allocate GPUs? | Kubernetes (native / Kueue) / NVIDIA Run:ai / Slurm / OpenShift AI / VMware Private AI / Undecided | PLAT | P1 | Scheduler standard and queue design |
| CMP-07 | How are GPU quotas, priorities and pre-emption decided between teams? | Free text | PLAT | P2 | Fair-share, quota and pre-emption policy |
| CMP-08 | What target GPU utilisation is expected, and what happens to idle allocations? | Free text | FIN | P2 | Utilisation targets and reclaim policy |
| CMP-09 | Is there a standard for CPU, memory and local NVMe per GPU node? | Yes / No / Partial / Unknown | INFRA | P2 | Node configuration baseline |
| CMP-10 | What is the hardware refresh / generation-mixing policy (e.g. Hopper and Blackwell in one cluster)? | Free text | INFRA | P3 | Lifecycle and heterogeneous cluster policy |
| CMP-11 | Are AI PCs / workstations (developer and edge inference) part of the standard? | Yes / No / Partial / Unknown | EA | P3 | Client and edge AI device standard |

## NET - Networking & Fabric

**Target standard:** STD-09 AI Network Fabric Standard  
**Intent:** Standardise compute (east-west), storage and front-end networks, segmentation and connectivity for the AI Factory.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| NET-01 | Which back-end (GPU-to-GPU) fabric technology is preferred? | InfiniBand / Ethernet with RoCE (e.g. NVIDIA Spectrum-X) / Ethernet with RoCE (Dell PowerSwitch / other ASIC) / No multi-node training planned / Undecided | NET | P1 | Compute fabric standard |
| NET-02 | What per-GPU network bandwidth is required (e.g. 200 / 400 / 800 Gb/s)? | 100 Gb/s / 200 Gb/s / 400 Gb/s / 800 Gb/s / Undecided | NET | P1 | Port speed and NIC / SuperNIC / DPU standard |
| NET-03 | Will storage traffic use a dedicated network separate from compute and front-end traffic? | Yes / No / Partial / Unknown | NET | P1 | Network plane separation |
| NET-04 | What topology and oversubscription ratio are acceptable (rail-optimised, non-blocking fat-tree, etc.)? | Free text | NET | P1 | Topology and oversubscription rules |
| NET-05 | How will tenants and environments be segmented (VRF, VLAN / VXLAN, micro-segmentation)? | Free text | NET | P1 | Segmentation model |
| NET-06 | What connectivity is required to existing data centers, public clouds and edge sites, and at what bandwidth? | Free text | NET | P2 | WAN / interconnect standard |
| NET-07 | Is DPU / SmartNIC offload (security, storage, networking) required? | Yes / No / Partial / Unknown | NET | P3 | DPU usage policy |
| NET-08 | How will inference endpoints be exposed (internal load balancer, API gateway, service mesh, ingress)? | Free text | PLAT | P2 | North-south exposure pattern |
| NET-09 | What IP addressing, DNS and naming conventions apply to AI Factory networks? | Free text | NET | P1 | IPAM, DNS and naming |

## PLT - Platform Software, Kubernetes & AI Software Stack

**Target standard:** STD-10 Platform Software & AI Stack Standard  
**Intent:** Standardise the OS, container platform, AI software stack and provisioning automation.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| PLT-01 | Which container / virtualisation platform is standard for AI workloads? | Red Hat OpenShift / Upstream Kubernetes / VMware vSphere / VCF with Private AI / Rancher / RKE2 / Bare metal + Slurm / Multiple / Undecided | PLAT | P1 | Approved runtime platforms |
| PLT-02 | Which AI software stack(s) are approved? | NVIDIA AI Enterprise (NIM / NeMo / Triton) / Red Hat OpenShift AI / Open-source (vLLM / Ray / KServe / Kubeflow) / AMD ROCm stack / Hugging Face (incl. Dell Enterprise Hub) / Undecided | PLAT | P1 | Approved AI software stacks |
| PLT-03 | What is the standard OS and driver / firmware baseline for GPU nodes? | Free text | INFRA | P1 | Golden image and driver / firmware matrix |
| PLT-04 | How will bare-metal provisioning and cluster build be automated (e.g. Dell Omnia, OpenManage, Ansible, Terraform)? | Free text | PLAT | P1 | Infrastructure-as-code and provisioning toolchain |
| PLT-05 | Is GitOps required for cluster and application configuration? | Yes / No / Partial / Unknown | PLAT | P2 | GitOps / configuration management |
| PLT-06 | What is the patching and upgrade cadence for firmware, OS, drivers, Kubernetes and AI stack? | Free text | OPS | P2 | Patch and upgrade policy |
| PLT-07 | Is there an approved internal container registry and base-image policy? | Yes / No / Partial / Unknown | SEC | P1 | Image registry and base-image standard |
| PLT-08 | Will developers get self-service workspaces (notebooks, IDEs, sandboxes)? Through which portal? | Free text | PLAT | P2 | Developer self-service and golden paths |
| PLT-09 | How many environments are required (dev / test / staging / prod) and are they physically or logically separated? | Free text | PLAT | P1 | Environment strategy |
| PLT-10 | Is an air-gapped / disconnected deployment required for any environment? | Yes / No / Partial / Unknown | SEC | P1 | Disconnected install and artefact mirroring |

## MLO - Model Lifecycle - MLOps / LLMOps

**Target standard:** STD-11 Model Lifecycle (MLOps / LLMOps) Standard  
**Intent:** Standardise how models are sourced, trained, evaluated, approved, served, monitored and retired.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| MLO-01 | Which model sources are permitted? | Commercial API models / Open-weight models (Llama / Mistral / Qwen / etc.) / NVIDIA NIM-packaged models / Hugging Face / Dell Enterprise Hub / Internally trained models / Vendor-embedded models | DS | P1 | Approved model sources and licences |
| MLO-02 | Is there a model approval / allow-list process (licence, security scan, evaluation) before a model can be used? | Yes / No / Partial / Unknown | SEC | P1 | Model onboarding and allow-list |
| MLO-03 | Which model registry and experiment-tracking tools are standard (e.g. MLflow)? | Free text | DS | P2 | Registry and experiment tracking |
| MLO-04 | What metadata is mandatory for every registered model (owner, data sources, intended use, risk tier, eval results, model card)? | Free text | CDO | P2 | Model card / registration schema |
| MLO-05 | Which inference serving runtimes are standard (e.g. NIM, Triton, vLLM, KServe)? | Free text | PLAT | P1 | Serving runtime standard |
| MLO-06 | What latency, throughput and availability SLOs apply to inference endpoints by tier? | Free text | OPS | P2 | Inference SLO tiers |
| MLO-07 | What offline evaluation (accuracy, safety, red-teaming) is required before promotion to production? | Free text | DS | P2 | Pre-release evaluation gates |
| MLO-08 | How are models monitored in production (drift, quality, toxicity, cost per request)? | Free text | DS | P2 | Production model monitoring |
| MLO-09 | Are guardrails (input / output filtering, topic control, jailbreak detection) mandatory for GenAI apps? | Yes / No / Partial / Unknown | SEC | P1 | Guardrail requirements (e.g. NeMo Guardrails or equivalent) |
| MLO-10 | What is the policy for fine-tuning (who may fine-tune, on which data, approval required)? | Free text | DS | P2 | Fine-tuning policy |
| MLO-11 | Is a central AI / LLM gateway required for routing, rate limiting, logging and cost tracking of model calls? | Yes / No / Partial / Unknown | PLAT | P2 | AI gateway standard |
| MLO-12 | How are models versioned, rolled back and retired? | Free text | DS | P3 | Versioning, rollback and decommissioning |

## AGT - Agentic AI & Tool Integration

**Target standard:** STD-12 Agentic AI Standard  
**Intent:** Define safe patterns for AI agents that call tools, APIs and data on behalf of users.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| AGT-01 | Are autonomous or semi-autonomous agents in scope for the first 12 months? | Yes / No / Partial / Unknown | EXEC | P1 | Agentic AI scope |
| AGT-02 | Which agent frameworks / protocols are approved (e.g. MCP, A2A, LangGraph, NVIDIA AI Blueprints / Agent toolkits)? | Free text | EA | P2 | Approved agent frameworks and protocols |
| AGT-03 | What actions may agents take without human approval (read-only, draft, transact, change systems)? | Free text | LEGAL | P1 | Agent autonomy levels and approval matrix |
| AGT-04 | How do agents authenticate to tools and data - user delegation (on-behalf-of) or service identity? | On-behalf-of the end user / Dedicated agent service identity / Both by risk tier / Undecided | SEC | P1 | Agent identity and least-privilege |
| AGT-05 | Is a registry of approved tools / MCP servers that agents may call required? | Yes / No / Partial / Unknown | SEC | P2 | Tool / MCP server registry |
| AGT-06 | What logging and traceability is required for every agent step (prompts, tool calls, results)? | Free text | SEC | P2 | Agent audit trail |
| AGT-07 | What spend, rate and loop limits apply to agents? | Free text | FIN | P2 | Agent runtime guardrails |

## SEC - Security, Identity & Zero Trust

**Target standard:** STD-13 AI Security & Identity Standard  
**Intent:** Apply enterprise security baselines to AI infrastructure, data, models and applications.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| SEC-01 | Which identity provider(s) are authoritative for users and service accounts (AD, Entra ID, Okta, LDAP)? | Free text | SEC | P1 | Identity source of truth and SSO |
| SEC-02 | What access model is required: RBAC, ABAC (tag / attribute based) or both? | RBAC / ABAC / RBAC + ABAC / Undecided | SEC | P1 | Authorisation model |
| SEC-03 | Is encryption at rest mandatory on all storage, and must keys be held in an external KMS / HSM? | Yes / No / Partial / Unknown | SEC | P1 | Encryption at rest and key management |
| SEC-04 | Is TLS / mTLS mandatory for all data-in-transit, including inside the cluster and storage networks? | Yes / No / Partial / Unknown | SEC | P1 | Encryption in transit |
| SEC-05 | What secrets-management solution is standard (e.g. HashiCorp Vault, CyberArk, cloud KMS)? | Free text | SEC | P1 | Secrets management |
| SEC-06 | Which security frameworks apply to AI applications (e.g. OWASP Top 10 for LLM Apps, MITRE ATLAS, NIST CSF 2.0)? | OWASP Top 10 for LLM Applications / MITRE ATLAS / NIST CSF 2.0 / NIST SP 800-53 / ISO/IEC 27001 / CIS Benchmarks / Internal baseline only | SEC | P1 | Security control frameworks |
| SEC-07 | How are prompt injection, data exfiltration via prompts and insecure output handling mitigated? | Free text | SEC | P2 | GenAI application security controls |
| SEC-08 | Is software / model supply-chain security required (SBOM, image signing, model weight scanning and provenance)? | Yes / No / Partial / Unknown | SEC | P1 | Supply-chain security (SBOM, signing, scanning) |
| SEC-09 | Is privileged access to infrastructure (iDRAC, OneFS, switches, Kubernetes admin) brokered through a PAM solution? | Yes / No / Partial / Unknown | SEC | P1 | Privileged access management |
| SEC-10 | Which logs must go to the SIEM, and what is the retention period? | Free text | SEC | P2 | Security logging and SIEM integration |
| SEC-11 | Is AI red-teaming / penetration testing required before go-live and periodically? | Yes / No / Partial / Unknown | SEC | P2 | Offensive testing cadence |
| SEC-12 | What hardware security requirements apply (secure boot, silicon root of trust, firmware signing, TPM)? | Free text | INFRA | P1 | Hardware / firmware security baseline |

## PRV - Privacy & Regulatory Compliance

**Target standard:** STD-14 Privacy & Regulatory Compliance Standard  
**Intent:** Capture regulatory obligations that constrain data use, model behaviour and evidence collection.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| PRV-01 | Which regulations apply to data and AI processed on the platform? | GDPR / CCPA / CPRA / HIPAA / PCI DSS / SOX / GLBA / EU AI Act / DORA / NIS2 / FedRAMP / FISMA / Industry-specific / None identified | LEGAL | P1 | Applicable regulation register |
| PRV-02 | Is PII / PHI / PCI data permitted in prompts, training data or RAG indexes? Under what controls? | Free text | LEGAL | P1 | Sensitive data in AI rules |
| PRV-03 | Is a DPIA / privacy impact assessment required for AI use cases processing personal data? | Yes / No / Partial / Unknown | LEGAL | P2 | Privacy assessment requirements |
| PRV-04 | How must data-subject rights (access, deletion, objection) be honoured across models, embeddings and logs? | Free text | LEGAL | P2 | Data-subject rights handling |
| PRV-05 | What audit evidence must the platform produce automatically (access logs, approvals, model lineage)? | Free text | LEGAL | P2 | Compliance evidence and audit readiness |
| PRV-06 | Are there contractual restrictions on customer or partner data being used for AI? | Yes / No / Partial / Unknown | LEGAL | P1 | Contractual data-use restrictions |
| PRV-07 | Which certifications / attestations must the AI Factory support (SOC 2, ISO 27001, ISO 42001, HITRUST)? | Free text | LEGAL | P3 | Certification roadmap |

## OPS - Operations, Observability & Support

**Target standard:** STD-15 AI Operations & Observability Standard  
**Intent:** Standardise monitoring, alerting, SLOs, incident management and vendor support for the AI Factory.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| OPS-01 | Which observability stack is standard (e.g. Prometheus / Grafana, Splunk, Datadog, Dynatrace, ELK)? | Free text | OPS | P1 | Observability tooling |
| OPS-02 | Which Dell management tools will be used (e.g. OpenManage Enterprise, iDRAC, APEX AIOps / CloudIQ, PowerScale InsightIQ)? | OpenManage Enterprise / iDRAC / APEX AIOps (CloudIQ) / PowerScale InsightIQ / SmartFabric / switch management / None / third-party only | OPS | P1 | Infrastructure management tooling |
| OPS-03 | Which GPU, fabric and storage telemetry must be collected (e.g. DCGM metrics, ECC errors, link errors, throughput)? | Free text | OPS | P2 | Mandatory telemetry and metrics |
| OPS-04 | What platform SLOs (availability, job start time, storage latency) will be published to tenants? | Free text | OPS | P2 | Platform SLOs and SLAs |
| OPS-05 | Which ITSM tool and processes (incident, change, problem) govern the AI Factory? | Free text | OPS | P1 | ITSM integration |
| OPS-06 | What support model is expected from Dell and partners (ProSupport level, managed services, resident engineers)? | Free text | PROC | P1 | Vendor support model |
| OPS-07 | What is the on-call model and support hours for platform vs. application teams? | Free text | OPS | P2 | Support tiers and on-call RACI |
| OPS-08 | Is automated remediation / AIOps expected for common failures (node drain, GPU reset, job requeue)? | Yes / No / Partial / Unknown | OPS | P3 | Automated remediation runbooks |
| OPS-09 | What is the change-freeze and maintenance-window policy for a shared GPU cluster with long-running jobs? | Free text | OPS | P2 | Maintenance window policy |

## BCR - Resilience, Backup & Cyber Recovery

**Target standard:** STD-16 Resilience, Backup & Cyber Recovery Standard  
**Intent:** Define what must be protected (data, models, checkpoints, configs) and how fast it must recover.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| BCR-01 | Which AI assets are business-critical and must be backed up (training data, curated tables, model weights, checkpoints, vector indexes, configs)? | Raw / source data / Curated lakehouse tables / Model weights / Training checkpoints / Vector indexes / Prompts and logs / Platform configuration / IaC | INFRA | P1 | Protection scope |
| BCR-02 | What RPO / RTO apply to each critical AI service? | Free text | OPS | P1 | RPO / RTO tiers |
| BCR-03 | Is a secondary site / DR AI Factory required, or is degraded service acceptable during disaster? | Active-active / Active-passive DR site / Cloud DR / Backup-only restore / No DR required | EA | P1 | DR topology |
| BCR-04 | Is an isolated cyber-recovery vault (air-gapped, immutable copies) required? | Yes / No / Partial / Unknown | SEC | P2 | Cyber recovery vault (e.g. PowerProtect Cyber Recovery) |
| BCR-05 | Which backup software is standard (e.g. PowerProtect Data Manager, Veeam, Commvault)? | Free text | INFRA | P2 | Backup tooling |
| BCR-06 | How often must restores and DR failovers be tested? | Free text | OPS | P2 | Recovery testing cadence |
| BCR-07 | What checkpointing frequency is required for long training jobs to tolerate node / GPU failure? | Free text | DS | P2 | Checkpoint policy |

## FIN - FinOps, Chargeback & Capacity Management

**Target standard:** STD-17 AI FinOps & Capacity Standard  
**Intent:** Make AI Factory cost transparent and fairly allocated, and plan capacity ahead of demand.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| FIN-01 | What funding model will be used for the AI Factory? | Central IT funded / Showback only / Chargeback to business units / Hybrid (core central / usage charged) / Undecided | FIN | P1 | Funding and allocation model |
| FIN-02 | Which cost units will be metered (GPU-hours, storage TB-month, tokens, API calls, network)? | GPU-hours / CPU-hours / Storage TB-month / Tokens / requests / Data egress / Licences / Support / services | FIN | P2 | Metering units and rate card |
| FIN-03 | Which mandatory tags / labels are required on every workload and dataset (cost center, owner, project, environment, data class)? | Free text | FIN | P1 | Mandatory tagging / labelling standard |
| FIN-04 | Is a consumption-based procurement model preferred (e.g. Dell APEX / as-a-service) over capex? | Capex purchase / Opex / as-a-service / Lease / Mixed / Undecided | PROC | P1 | Procurement model |
| FIN-05 | What is the capacity planning horizon and trigger for expansion (utilisation %, queue wait time)? | Free text | INFRA | P2 | Capacity triggers |
| FIN-06 | How will on-prem cost-per-unit be benchmarked against public cloud alternatives? | Free text | FIN | P3 | TCO benchmarking |
| FIN-07 | Are budgets and alerts required per team / project? | Yes / No / Partial / Unknown | FIN | P2 | Budgets and spend alerts |

## FAC - Data Center Facilities & Sustainability

**Target standard:** STD-18 AI Data Center & Sustainability Standard  
**Intent:** Confirm the site can host high-density AI racks and set energy / sustainability targets.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| FAC-01 | What is the available power per rack today and the maximum achievable (kW / rack)? | Free text | FAC | P1 | Rack power density standard |
| FAC-02 | What cooling is available or planned? | Air cooling only / Rear-door heat exchangers / Direct liquid cooling (DLC) / Immersion cooling / Unknown | FAC | P1 | Cooling standard |
| FAC-03 | What total facility power (MW) and floor space can be allocated to the AI Factory over 36 months? | Free text | FAC | P1 | Site capacity plan |
| FAC-04 | Are pre-integrated rack-scale deliveries acceptable (e.g. Dell Integrated Rack Scalable Systems), and are there dock / weight / floor-loading limits? | Free text | FAC | P1 | Rack delivery and site-readiness checklist |
| FAC-05 | Are there sustainability targets (PUE, carbon intensity, renewable %, heat reuse) the AI Factory must report against? | Free text | FAC | P2 | Sustainability KPIs and reporting |
| FAC-06 | Is power capping / energy-aware scheduling required for GPUs? | Yes / No / Partial / Unknown | OPS | P3 | Energy management policy |
| FAC-07 | What are the e-waste, asset disposal and data-sanitisation requirements at end of life? | Free text | PROC | P3 | Asset retirement and sanitisation |

## ORG - Operating Model, Skills & Adoption

**Target standard:** STD-19 AI Operating Model & Skills Standard  
**Intent:** Define the teams, roles, skills and engagement model that run and consume the AI Factory.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| ORG-01 | What operating model is preferred for AI delivery? | Centralised AI CoE / Federated (hub-and-spoke) / Decentralised per business unit / Undecided | EXEC | P1 | AI operating model |
| ORG-02 | Which platform roles exist today and which must be hired or contracted (platform SRE, ML engineer, data engineer, AI security)? | Free text | HR | P1 | Role catalogue and staffing plan |
| ORG-03 | What training / certification paths are required for platform and consumer teams? | Free text | HR | P2 | Skills and certification paths |
| ORG-04 | How will tenants onboard to the platform (request form, SLA, onboarding checklist)? | Free text | PLAT | P2 | Tenant onboarding process |
| ORG-05 | What role will Dell Professional Services / partners play (design, deployment, residency, managed service)? | Free text | PROC | P1 | Partner engagement model |
| ORG-06 | Is there an acceptable-use policy and mandatory training for employees using GenAI tools? | Yes / No / Partial / Unknown | HR | P2 | GenAI acceptable-use and literacy training |
| ORG-07 | How will internal community, documentation and reusable assets (templates, blueprints) be shared? | Free text | PLAT | P3 | Inner-source and knowledge sharing |

## ARC - Architecture Standards, Interoperability & Vendor Strategy

**Target standard:** STD-20 Reference Architecture, Naming & Exception Standard  
**Intent:** Lock in reference architectures, naming conventions, interoperability and the exception process that all other standards depend on.

| ID | Question | Options | Owner | Pri. | Drives |
|---|---|---|---|---|---|
| ARC-01 | Which Dell AI Factory reference architecture / validated design will be the baseline (e.g. Dell AI Factory with NVIDIA, with AMD, with Intel)? | Dell AI Factory with NVIDIA / Dell AI Factory with AMD / Dell AI Factory with Intel / Multi-vendor / Undecided | EA | P1 | Baseline reference architecture |
| ARC-02 | Which existing enterprise architecture standards (cloud, data, security, integration) must the AI Factory inherit? | Free text | EA | P1 | Inherited enterprise standards |
| ARC-03 | What naming conventions apply to clusters, namespaces, storage zones / buckets, datasets, models and endpoints? | Free text | EA | P1 | Naming convention standard |
| ARC-04 | What open standards / APIs are mandatory to avoid lock-in (S3, NFS, Iceberg, OpenAI-compatible APIs, Kubernetes, OpenTelemetry)? | S3 API / NFS / POSIX / Apache Iceberg / OpenAI-compatible inference API / Kubernetes APIs / OpenTelemetry / ONNX / MCP | EA | P1 | Mandatory open interfaces |
| ARC-05 | What is the multi-vendor / exit strategy for hardware, software and model providers? | Free text | PROC | P2 | Vendor diversification and exit plan |
| ARC-06 | Which architecture review board approves new patterns and deviations, and with what SLA? | Free text | EA | P1 | Architecture review and exception process |
| ARC-07 | How will standards be published, versioned and enforced (wiki, policy-as-code, CI checks, admission controllers)? | Free text | EA | P2 | Standards publication and enforcement mechanism |
| ARC-08 | Which documentation artefacts are mandatory per AI solution (HLD, LLD, threat model, runbook, model card)? | High-level design / Low-level design / Threat model / Data flow diagram / Runbook / Model card / AI impact assessment / DR plan | EA | P2 | Mandatory solution documentation |

## Maturity scale

1. Initial - ad hoc, undocumented, person-dependent
2. Repeatable - some practices exist but are inconsistent across teams
3. Defined - documented enterprise standard, mostly followed
4. Managed - standard is measured, automated and enforced (policy-as-code, dashboards)
5. Optimising - continuously improved from metrics and feedback; exceptions are rare

## Dell AI Factory component reference

Verify names and capabilities with your Dell account team.

| Layer | Component | Role | Domains |
|---|---|---|---|
| Storage engine | Dell PowerScale | Scale-out file storage (OneFS) for unstructured AI data; NFS / SMB / S3 / HDFS; NFS over RDMA and GPUDirect Storage for GPU data paths | STO, BCR |
| Storage engine | Dell ObjectScale | S3-compatible object storage for data lakes, model artefacts and checkpoints | STO, LAK |
| Data engine | Dell Data Lakehouse / Data Analytics Engine | Federated SQL analytics and lakehouse (Trino / Starburst based, Apache Iceberg) | LAK, ING |
| Data engine | Spark-based Data Processing Engine | Distributed data preparation and transformation for AI pipelines | LAK, ING |
| Data engine | Data Search Engine / vector search | Hybrid keyword + semantic search and vector indexing for RAG and agents | RAG |
| Compute | Dell PowerEdge XE / R-series GPU servers | Accelerated compute for training, fine-tuning and inference (NVIDIA, AMD, Intel accelerators) | CMP, FAC |
| Network | Dell PowerSwitch / NVIDIA Spectrum-X / InfiniBand | Back-end GPU fabric, storage and front-end networks | NET |
| AI software | NVIDIA AI Enterprise (NIM | Model serving, customisation and guardrails stack in Dell AI Factory with NVIDIA | PLT, MLO, AGT |
| AI software | Dell Enterprise Hub on Hugging Face | Curated open models optimised for Dell infrastructure | MLO |
| Platform | Red Hat OpenShift AI / Kubernetes / Dell Container Storage Modules | Container platform and persistent storage integration for AI workloads | PLT, STO |
| Automation | Dell Omnia / OpenManage Enterprise / iDRAC | Bare-metal provisioning, cluster deployment and lifecycle management | PLT, OPS |
| Operations | APEX AIOps (CloudIQ) / InsightIQ | Infrastructure health, capacity and performance analytics | OPS, FIN |
| Protection | PowerProtect Data Manager / Cyber Recovery | Backup and isolated cyber-recovery vault for AI data and models | BCR |
| Facilities | Dell Integrated Rack Scalable Systems / liquid cooling | Pre-integrated, high-density racks with direct liquid cooling options | FAC |
| Services | Dell Professional Services / ProSupport / APEX | Design, deployment, managed services and as-a-service consumption | ORG, OPS, FIN |
