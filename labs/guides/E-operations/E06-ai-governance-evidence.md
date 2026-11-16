# E06 - AI governance evidence

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM | 3 h | GOV, PRV, MLO, DAT | D03-D07 completed (index, registered model, guardrail eval, agent traces); E01 scanner. |

Auditors and the AI council will ask the same questions for every use case: what is it, which model and data, who approved it, how was it tested, what did it do. This lab produces that evidence automatically for the finance assistant built in D03-D07 and lists what is still missing. **Note:** the governance frameworks (EU AI Act, NIST AI RMF, ISO/IEC 42001) decide which fields are mandatory; GOV-02 decides which apply to you.

## Steps

### Step 1 - [SIM] AI inventory entry
Create `labs/evidence/e06-inventory.yaml` for the use case: name, owner, business purpose, risk tier (`GOV-03`), users, model(s) and versions, data sources and classes, RAG index, agent tools, human oversight, go-live date, review date. One entry per model, agent and RAG application; this is the register `GOV-06` asks for.

### Step 2 - [SIM] Model card
Write `labs/evidence/e06-model-card.md` for `d04-lora-adapter`: base model and licence, fine-tuning data (`ai/finetune.jsonl`) and its hash, training run ID, evaluation results from D07 (base vs. adapter loss), guardrail and red-team results from D05, known limitations (D06 found number formatting and unsupported claims), intended and prohibited use.

### Step 3 - [SIM] Build the evidence pack
```bash
cd labs/env && ~/.venvs/aif/bin/python ops/evidence_pack.py
unzip -l ../evidence/e06-pack.zip
```
Expected: `11 files, 1 gaps` with `GAP: zero-trust scan has failing checks` (unless you closed them in E01), and `evidence for:` listing the questionnaire IDs covered (AGT-06, GOV-06, MLO-03 ... SEC-11). The pack contains the registry record with every version, alias, parameters and metrics; the training data hash; the RAG corpus inventory with ACLs; the guardrail/red-team output; the latest agent traces; the zero-trust scan; and the Git revision. `manifest.json` has a sha256 for each file.

### Step 4 - [SIM] Lineage: from table to answer
Trace one answer back to its sources and write the chain into the model card:
1. D06 trace: the SQL the agent ran and the documents it retrieved (`ai/traces/*.jsonl`).
2. Iceberg: `SELECT * FROM iceberg.consumption."daily_revenue$snapshots"` in Trino shows which snapshot the query read; B03 shows the source tables.
3. RAG: the document IDs and paths in the inventory point to `/ifs/...` source files.
4. Model: the registry version and run show the base model, adapter and training data hash.
Any link you cannot follow is a lineage gap (`DAT-07`). Production tools (OpenLineage/Marquez, the data catalog, MLflow lineage) automate this chain.

### Step 5 - [SIM] Audit-log export
List the logs the SIEM needs and where they come from in the lab: S3 access logs, Trino query log (`docker compose logs trino`), MLflow registry events, agent traces, Kubernetes audit log, OneFS audit (E01 Step 6). Pick a retention for each and check who can delete them.

### Step 6 - [SIM] Review
Hand the pack, inventory entry and model card to a colleague acting as auditor and ask three questions: who approved this version, which data trained it, and what happens if a user asks for their data to be deleted (D03 deletion). Every question that needs you to explain verbally is a gap.

## Verify
- [ ] Inventory entry and model card written.
- [ ] Evidence pack produced, gaps listed, checksums in the manifest.
- [ ] Lineage traced from answer to source, gaps recorded.
- [ ] Audit log sources and retention listed.

## Record for the standards
`GOV-05` impact assessment. `GOV-06` AI inventory. `GOV-08` transparency. `MLO-04` mandatory model metadata. `DAT-07` end-to-end lineage. `PRV-05` automatic audit evidence. `SEC-10` logs to the SIEM and retention.

## Cleanup
Keep the pack for X01; otherwise `rm labs/evidence/e06-pack.zip`.
