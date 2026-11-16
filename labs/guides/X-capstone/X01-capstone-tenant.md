# X01 - Capstone: onboard a business-unit tenant

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM end-to-end / DEMO and HW for the Dell-specific steps | 1-2 days | All | All earlier tracks, or at least A09, B02, B03, C05, D03, D05, E01, E03, E05. |

Onboard a new business unit, "Treasury", onto the AI Factory using only the standards you drafted from the questionnaire. Every step points to the lab that taught it. The output is a tenant that works and a checklist showing each STD clause as met, or as an approved exception.

## Steps

### Step 1 - [SIM] Intake
Fill a one-page request: owner, cost center, data classes, users and groups, expected GPU and storage demand, first use case (a guarded RAG assistant over treasury policies). Assign the risk tier (`GOV-03`).

### Step 2 - [SIM] Storage tenancy (A02, A09)
```bash
cd labs/env && bin/s3 s3 mb s3://bu-treasury
```
Create an S3 identity limited to that bucket (A09 Step 2 pattern), enable versioning only where the standard asks, and set a lifecycle rule. *(DEMO)* OneFS: access zone `treasury`, `/ifs/bu-treasury`, SmartQuota with advisory and hard thresholds, snapshot schedule (A02, A03).

### Step 3 - [SIM] Lakehouse (B02, B03)
In Trino create schema `iceberg.treasury` with location `s3://warehouse/treasury/`, load one table, and add the governance rules (B03) so only `treasury` users see it and the `account_no` column is masked for analysts.

### Step 4 - [SIM] Compute queue (C05)
Namespace `team-treasury` with a Kueue `LocalQueue` on a `ClusterQueue` in the shared cohort (2 fake GPUs nominal, borrowing limit 2), default-deny NetworkPolicy and RoleBinding (E01 Step 4), and the cost-label admission policy (E05 Step 3).

### Step 5 - [SIM] Guarded RAG assistant (D03, D05)
Add three treasury documents to `search/corpus.jsonl` with `acl: ["treasury"]`, re-ingest, and confirm a non-treasury user gets no treasury hits. Run the D05 guardrail suite against the assistant; the release gate must pass.

### Step 6 - [SIM] Operate (C08, E03, E04, E05)
Add the tenant to the Grafana dashboards, run `ops/backup_restore.py backup` and a restore of the index, add the bucket to the DR replication scope, and add `bu-treasury` and `team-treasury` to the showback (`BUCKET_TENANT` in `ops/showback.py`).

### Step 7 - [SIM] Prove it
```bash
~/.venvs/aif/bin/python ops/zt_scan.py
~/.venvs/aif/bin/python ops/evidence_pack.py --out ../evidence/x01-treasury-pack.zip
```
Record the onboarding time, end to end, and the number of manual steps. Target: a second tenant takes a day and every manual step has an automation ticket.

### Step 8 - [SIM] Standards checklist
For each standard STD-01 to STD-20 (generated from [questions.yaml](../../../questionnaire/questions.yaml)), mark each clause: met (with the evidence file), not applicable, or exception (with approver and expiry date). Present the checklist to the AI council as the template for every future tenant.

## Verify
- [ ] Treasury users can query their data and assistant; others cannot.
- [ ] Queue, quota, labels, backup, DR scope and showback in place.
- [ ] Scan and evidence pack stored; onboarding time recorded.
- [ ] Every STD clause met or an approved exception.

## Record for the standards
`GOV-12` exception process. `PLT-08` self-service onboarding. `STO-06` tenancy. `CMP-05` queues and quotas. `RAG-03` ACL-filtered retrieval. `FIN-03` mandatory labels. `BCR-01` protected assets. `PRV-05` audit evidence.

## Cleanup
Delete `team-treasury`, `s3://bu-treasury`, `iceberg.treasury` and the treasury documents, or keep the tenant as the reference implementation.
