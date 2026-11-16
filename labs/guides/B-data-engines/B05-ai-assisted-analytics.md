# B05 - AI-assisted analytics

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Trino AI functions + Ollama) / DEMO (Analytics Engine AI features) | 3 h | LAK, AGT, SEC | B01-B03; `make up PROFILES="core ai"` |

[DEMO] Starburst-based engines are adding AI features: natural-language query, AI SQL functions and agent/MCP access. Exact names and availability depend on the release, so check the Dell Data Analytics Engine documentation for your version. The controls tested here apply whichever product you use.
[SIM] Trino 476 includes **AI functions** (`ai_analyze_sentiment`, `ai_classify`, `ai_extract`, `ai_gen`, `ai_mask`, `ai_translate`). The lab catalog `llm` (`labs/env/trino/catalog/llm.properties`) points them at Ollama's OpenAI-compatible API.

## Prerequisites
```bash
cd labs/env
docker compose exec ollama ollama pull qwen2.5:1.5b       # the model llm.properties uses
. ~/.venvs/aif/bin/activate && pip install trino requests
docker compose -f docker-compose.yml -f docker-compose.governance.yml --profile core up -d --force-recreate trino   # B03 governance on
```
Small CPU models are fast but make mistakes. For better results, set `ai.model=qwen2.5:7b` (pull it first) or point `ai.openai.endpoint` at a NIM endpoint (D01). Trino reads catalog files at startup, so recreate the container after you change them.

## Steps

### Step 1 - AI functions in SQL
```bash
bin/trino --execute "SHOW FUNCTIONS FROM llm.ai"
bin/trino --execute "SELECT llm.ai.ai_analyze_sentiment('The new GPU cluster is fantastic')"                         # positive
bin/trino --execute "SELECT llm.ai.ai_classify('My invoice was charged twice', ARRAY['billing','technical','sales'])"  # billing
bin/trino --execute "SELECT llm.ai.ai_gen('Write a one-line summary of what a lakehouse is')"
```

### Step 2 - Classify support tickets in bulk
```bash
bin/trino --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.curated WITH (location='s3://warehouse/curated');
CREATE OR REPLACE TABLE iceberg.curated.tickets AS SELECT * FROM (VALUES
  (1, 'I was billed twice for the same order'),
  (2, 'The dashboard will not load since this morning'),
  (3, 'Can I get a quote for 20 more licences?'),
  (4, 'Password reset email never arrives'),
  (5, 'Refund has not reached my card')) AS t(id, body)"
bin/trino --execute "
SELECT id, body, llm.ai.ai_classify(body, ARRAY['billing', 'technical', 'sales']) AS category,
       llm.ai.ai_analyze_sentiment(body) AS sentiment
FROM iceberg.curated.tickets"
```
Write down the expected label for each ticket and count the correct ones. That is your accuracy on this set.
Expect occasional `Failed to parse AI response` errors with the 1.5B model, when it does not answer in the required format. Record the failure rate. It is an argument for a larger model or NIM, and for wrapping AI calls in `try(...)` in production SQL.

### Step 3 - Cost and latency of AI in SQL
```bash
time bin/trino --execute "SELECT count(llm.ai.ai_analyze_sentiment(body)) FROM iceberg.curated.tickets"
```
Every row is one LLM call. Multiply the time per row by the row count of a real table before allowing AI functions in production. Decide whether they are allowed only in batch pipelines, with a `LIMIT`, or behind a resource group.

### Step 4 - Natural language to SQL, under the caller's identity
`labs/env/ai/nl2sql.py` reads the table schema as the calling user, asks the LLM for SQL, rejects anything that is not `SELECT`/`WITH`, and runs the query **as that user**. If Trino returns an error, the script sends the error back to the model and lets it retry, up to three attempts.
```bash
python ai/nl2sql.py --user fin "total order amount per customer region"
python ai/nl2sql.py --user ana "total order amount per customer region"
python ai/nl2sql.py --user ana "list 3 customer names and emails"
python ai/nl2sql.py --user ana "delete all orders"
```
Expected (SIM run, recorded by Devin):
- `fin` gets all four regions. The 1.5B model sometimes needs a retry or fails after three attempts, which is normal for a small model.
- `ana` gets only `EMEA`, and names/emails come back as `C***` / `***masked***`.
- `delete all orders` is refused before it reaches the engine. Even if it ran, B03 denies `ana` deletes.

The key point is that the generated SQL runs with the user's own permissions, so the LLM cannot widen access. Check the opposite design too: if a shared service account ran the queries, `ana` would see all regions unmasked.

### Step 5 - Measure NL-to-SQL accuracy
Write 10 business questions with known correct answers (e.g. "orders in 1995", "top segment by revenue"). Run each one 3 times and record: correct / wrong answer / no valid SQL. Repeat with a bigger model (`LLM_MODEL=qwen2.5:7b python ai/nl2sql.py ...`).

### Step 6 - Agent access over MCP (design + optional run)
An MCP (Model Context Protocol) server exposes governed data to AI agents as tools (e.g. `list_tables`, `describe_table`, `run_query`).
1. Choose an MCP server for Trino/Starburst (vendor-provided, or an open-source Trino MCP server). Check its maintenance status and licence before you use it.
2. Configure it with **per-user credentials or OAuth token pass-through**, not a shared admin account, so B03 policies still apply.
3. Allow-list read-only tools only. Log every tool call with the agent ID and the user it acted for.
4. Optional: connect it to an MCP-capable client and repeat Step 4's questions as `ana`.
D06 builds on this with a full agent.

## Verify
- [ ] AI functions work from SQL, and accuracy/failure rates on the ticket set are recorded.
- [ ] Generated SQL respects B03 row filters and masks.
- [ ] Non-SELECT generated statements are rejected.
- [ ] The MCP access pattern (identity pass-through, read-only tools, logging) is documented.

## Record for the standards
`LAK-08` supported consumer tools (AI functions, NL query, MCP), and where they are allowed. `MLO-02` model allow-list for the LLM behind SQL. `AGT-04` agent identity and least privilege (identity pass-through). `AGT-05` MCP server registry. `GOV-07` human review of generated SQL for high-impact use.

## Cleanup
```bash
bin/trino --execute "DROP TABLE iceberg.curated.tickets"
docker compose --profile core up -d --force-recreate trino      # governance off again
```
