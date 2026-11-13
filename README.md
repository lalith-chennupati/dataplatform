# dataplatform

Enterprise standards for the Dell AI Factory and Dell AI Data Platform.

## Contents

| Path | What it is |
|---|---|
| `questionnaire/questions.yaml` | Source of truth: 20 domains, ~190 questions, owner role, priority and the standard clause each answer drives |
| `questionnaire/ai-factory-standards-questionnaire.xlsx` | Working edition with drop-downs, status tracking, respondent sheet, maturity scorecard, standards map |
| `questionnaire/ai-factory-standards-questionnaire.docx` | Interview / workshop edition (landscape, one domain per page) |
| `questionnaire/ai-factory-standards-questionnaire.md` | GitHub-readable edition |
| `tools/build_questionnaire.py` | Regenerates the three editions from the YAML |
| `labs/README.md` | Lab catalog: 43 hands-on labs across Dell AI Factory and AI Data Platform features, with environment tier (SIM / DEMO / HW) and the questionnaire domains each lab informs |

## How the questionnaire is used

1. Fill in **Respondents** in the workbook (one person per role code).
2. Filter **Questionnaire** by `Owner` and send each stakeholder their rows, or run workshops with the DOCX edition.
3. Answer **P1** questions first. These block the Day-0 architecture, procurement and security baseline.
4. Score current and target maturity (1-5) per domain on the **Maturity** sheet.
5. Use **Standards Map** to turn the answers into the standards documents `STD-01` to `STD-20`.

## Domains -> target standards

| Code | Domain | Target standard |
|---|---|---|
| STR | Strategy, Business Alignment & Use Cases | STD-01 AI Strategy & Use-Case Intake |
| GOV | AI Governance, Risk & Responsible AI | STD-02 AI Governance & Responsible AI Policy |
| DAT | Data Strategy, Governance & Lifecycle | STD-03 Data Governance, Classification & Lifecycle |
| STO | Storage Engines (PowerScale / ObjectScale) | STD-04 AI Storage Services |
| LAK | Data Engines: Lakehouse, Processing & Analytics | STD-05 Lakehouse & Data Engine |
| ING | Data Ingestion, Integration & Pipelines | STD-06 Data Ingestion & Pipeline |
| RAG | Retrieval, Vector Search & Knowledge | STD-07 RAG & Vector Search |
| CMP | Compute & Accelerators | STD-08 AI Compute & Accelerator |
| NET | Networking & Fabric | STD-09 AI Network Fabric |
| PLT | Platform Software, Kubernetes & AI Stack | STD-10 Platform Software & AI Stack |
| MLO | Model Lifecycle (MLOps / LLMOps) | STD-11 Model Lifecycle |
| AGT | Agentic AI & Tool Integration | STD-12 Agentic AI |
| SEC | Security, Identity & Zero Trust | STD-13 AI Security & Identity |
| PRV | Privacy & Regulatory Compliance | STD-14 Privacy & Regulatory Compliance |
| OPS | Operations, Observability & Support | STD-15 AI Operations & Observability |
| BCR | Resilience, Backup & Cyber Recovery | STD-16 Resilience, Backup & Cyber Recovery |
| FIN | FinOps, Chargeback & Capacity | STD-17 AI FinOps & Capacity |
| FAC | Data Center Facilities & Sustainability | STD-18 AI Data Center & Sustainability |
| ORG | Operating Model, Skills & Adoption | STD-19 AI Operating Model & Skills |
| ARC | Architecture, Interoperability & Vendor Strategy | STD-20 Reference Architecture, Naming & Exceptions |

## Regenerating

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 tools/build_questionnaire.py
```

Edit `questionnaire/questions.yaml` and leave the generated files alone. Question IDs (`STO-03` etc.) come from each question's position in its domain, so add new questions at the end of a domain to keep existing IDs the same.

## Note on Dell product names

The Dell component names (PowerScale, ObjectScale, Data Lakehouse / Data Analytics Engine, PowerEdge XE, APEX AIOps, Omnia, etc.) are taken from Dell's public portfolio as it stood when this was written. Check them against the [Dell AI Data Platform page](https://www.dell.com/en-us/shop/artificial-intelligence/sc/ai-data-platform) and with your Dell account team before you publish the standards.
