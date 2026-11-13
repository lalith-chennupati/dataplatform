# Lab guides - how to use them

Each lab in the [catalog](../README.md) has a step-by-step guide here. Every guide follows the same layout:

1. **Header**: environment tier, time, the questionnaire domains it informs, prerequisite labs.
2. **Prerequisites**: what has to be running.
3. **Steps**: numbered, copy-paste commands with the output you should expect.
4. **Verify**: a checklist. Every item has to pass before you mark the lab done.
5. **Record for the standards**: which questionnaire IDs to answer from what you saw, and where.
6. **Cleanup**.

## Conventions

| Convention | Meaning |
|---|---|
| `[SIM]` / `[DEMO]` / `[HW]` before a step | The environment that step needs. Skip `[HW]` steps when you don't have the hardware and write "not tested - HW" in the evidence log. |
| `labs/env` | Working directory for SIM-tier commands (`cd labs/env` first). The stack is described in [L01](00-foundations/L01-lab-environment.md). |
| `$PS` | IP / FQDN of the PowerScale cluster (OneFS Simulator or real). `ssh root@$PS` opens the OneFS CLI (`isi ...`). |
| `$OBJ` | ObjectScale S3 endpoint URL (e.g. `https://objectscale.lab.local:9021`). In SIM it is the lab S3 at `http://s3:8333`, which the `bin/s3` helper already uses. |
| `$IDRAC` | iDRAC IP / FQDN. In SIM it is the Redfish mockup at `localhost:8000`. |
| `bin/s3`, `bin/trino`, `bin/spark-sql` | Helper wrappers in `labs/env/bin`. `S3_USER=finance bin/s3 ...` runs as the `finance` tenant. |

> **Validation status.** The SIM-tier stack and the steps marked `[SIM]` that use it were smoke-tested on a Linux VM with Docker. OneFS, ObjectScale, iDRAC, OpenManage, Omnia, NIM and GPU steps follow Dell / NVIDIA documentation but have **not** been run by the author. CLI flags change between releases, so check them against the docs for your version (`isi <command> --help` on OneFS) and correct the guide when they differ.

## Evidence log

Keep one evidence log per lab run, e.g. `labs/evidence/<lab-id>-<date>.md`, containing:

- date, who ran it, environment tier and product versions (`isi version`, Trino version, driver versions),
- the output of each Verify item (screenshots or pasted text),
- deviations from the guide and any defects found,
- the questionnaire answers you drafted (copy them into the Response column of the questionnaire workbook).

## Index

| Track | Guides |
|---|---|
| Foundations | [L00](00-foundations/L00-orientation.md), [L01](00-foundations/L01-lab-environment.md) |
| A - Storage engines | [A01](A-storage/A01-onefs-fundamentals.md), [A02](A-storage/A02-access-zones-quotas.md), [A03](A-storage/A03-snapshots-replication-worm.md), [A04](A-storage/A04-tiering.md), [A05](A-storage/A05-powerscale-automation.md), [A06](A-storage/A06-powerscale-kubernetes.md), [A07](A-storage/A07-hpc-data-path.md), [A08](A-storage/A08-metadata-discovery.md), [A09](A-storage/A09-objectscale-s3.md), [A10](A-storage/A10-s3-for-ai.md) |
| B - Data engines | [B01](B-data-engines/B01-federated-sql.md), [B02](B-data-engines/B02-iceberg-lakehouse.md), [B03](B-data-engines/B03-lakehouse-governance.md), [B04](B-data-engines/B04-data-processing-spark.md), [B05](B-data-engines/B05-ai-assisted-analytics.md), [B06](B-data-engines/B06-unstructured-search.md), [B07](B-data-engines/B07-gpu-vector-indexing.md) |
| C - Infrastructure | [C01](C-infrastructure/C01-idrac-redfish.md), [C02](C-infrastructure/C02-openmanage-enterprise.md), [C03](C-infrastructure/C03-omnia-cluster.md), [C04](C-infrastructure/C04-gpus-on-kubernetes.md), [C05](C-infrastructure/C05-gpu-scheduling-quotas.md), [C06](C-infrastructure/C06-ai-network-fabric.md), [C07](C-infrastructure/C07-facilities-readiness.md), [C08](C-infrastructure/C08-telemetry-aiops.md) |
| D - AI software | [D01](D-ai-software/D01-nim-inference.md), [D02](D-ai-software/D02-dell-enterprise-hub.md), [D03](D-ai-software/D03-rag-end-to-end.md), [D04](D-ai-software/D04-fine-tuning-lora.md), [D05](D-ai-software/D05-guardrails-evaluation.md), [D06](D-ai-software/D06-agentic-ai.md), [D07](D-ai-software/D07-mlops-pipeline.md), [D08](D-ai-software/D08-openshift-ai.md), [D09](D-ai-software/D09-ai-pc-edge.md) |
| E - Operations | [E01](E-operations/E01-zero-trust-baseline.md), [E02](E-operations/E02-ransomware-cyber-recovery.md), [E03](E-operations/E03-backup-restore-ai-assets.md), [E04](E-operations/E04-dr-drill.md), [E05](E-operations/E05-chargeback-capacity.md), [E06](E-operations/E06-ai-governance-evidence.md) |
| Capstone | [X01](X-capstone/X01-capstone-tenant.md) |
