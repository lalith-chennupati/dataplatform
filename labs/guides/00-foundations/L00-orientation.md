# L00 - AI Factory & AIDP architecture orientation

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| Paper (workshop) | 2 h | STR, ARC | Questionnaire workbook, current-state architecture diagrams |

## Prerequisites
- `questionnaire/ai-factory-standards-questionnaire.xlsx` open, with the `STR` and `ARC` rows filtered.
- Your current infrastructure, data-platform and security architecture diagrams, even if out of date.
- Attendees: enterprise architect (`EA`), infrastructure lead (`INFRA`), data lead (`CDO`/`DE`), security (`SEC`), and a business sponsor (`EXEC`) for steps 1 and 6.

## Steps

### Step 1 - Agree the outcomes (20 min)
1. Write the top 3-5 business outcomes on the board. Each must have a measurable KPI, e.g. "reduce claims-processing time by 30 %".
2. For each outcome, name the AI workload class: GenAI inference, RAG, agents, fine-tuning, classical ML, analytics.
3. Record the answers in `STR-01` and `STR-02`.

### Step 2 - Draw the AI Factory layer model (30 min)
Draw this skeleton and fill each box with **what you have today** (black) and **what the AI Factory adds** (red):

```
 ┌──────────────────────── Use cases & applications (copilots, RAG apps, agents) ───────────────────────┐
 │  AI software:  NVIDIA AI Enterprise (NIM, NeMo) | Dell Enterprise Hub (Hugging Face) | OSS (vLLM...)  │
 │  Platform:     Kubernetes / OpenShift / Slurm | GPU Operator | schedulers | MLOps                     │
 ├────────────────── Dell AI Data Platform ────────────────────────────────────────────────────────────┤
 │  Data engines:     Data Analytics Engine (SQL / federation) | Data Processing Engine (Spark)         │
 │                    Data Search Engine (keyword + vector search)                                       │
 │  Storage engines:  PowerScale (file, NFS/SMB/S3/HDFS)       | ObjectScale (S3 object)                 │
 ├────────────────── Infrastructure ───────────────────────────────────────────────────────────────────┤
 │  Compute: PowerEdge XE / R GPU servers | Network: PowerSwitch / Spectrum-X / InfiniBand              │
 │  Mgmt: iDRAC, OpenManage Enterprise, Omnia, APEX AIOps | Protection: PowerProtect, Cyber Recovery     │
 ├────────────────── Facilities & services ────────────────────────────────────────────────────────────┤
 │  Power / cooling (IRSS, DLC) | Dell Professional Services, ProSupport, APEX                           │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Step 3 - Trace one use case through the layers (30 min)
Take the highest-priority use case from Step 1 and trace its data:
1. **Source** (e.g. SharePoint, ERP) -> **landing** (PowerScale share or ObjectScale bucket) -> **prep** (Processing Engine) -> **serve** (Search Engine index / lakehouse table) -> **model** (NIM endpoint) -> **app**.
2. At every hop, write down who owns it, what data class it carries, and which security control applies.
3. Mark each hop as *exists*, *gap* or *decision needed*.

### Step 4 - Choose the reference architecture (15 min)
1. List the candidate Dell AI Factory variants (with NVIDIA / AMD / Intel) and any validated designs your Dell team proposed.
2. Score each on fit with your outcomes, skills, existing estate and supply chain.
3. Record the choice, or the shortlist, in `ARC-01`.

### Step 5 - Map gaps to labs (15 min)
For every *gap* or *decision needed* from Step 3, find the lab in the [catalog](../../README.md) that produces the evidence, and put the lab IDs into your lab plan.

### Step 6 - Agree the lab plan (10 min)
Confirm the labs, owners, environment tier (SIM / DEMO / HW) and dates. Book Dell Demo Center or hardware time for the DEMO/HW labs.

## Verify
- [ ] A one-page layer diagram with owners and gaps exists.
- [ ] One use case has been traced end to end.
- [ ] `STR-01`, `STR-02` and `ARC-01` have draft answers.
- [ ] A lab plan exists with owners and dates.

## Record for the standards
`STR-01`, `STR-02`, `STR-05`, `ARC-01`, `ARC-02`: copy the workshop output into the questionnaire Response column.

## Cleanup
None.
