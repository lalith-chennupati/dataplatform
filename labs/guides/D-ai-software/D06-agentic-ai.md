# D06 - Agentic AI with tool governance

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Ollama tool calling + Trino + Elasticsearch) / HW (NIM with tool calling, NVIDIA AI-Q / agent blueprints) | 3 h | AGT, SEC, OPS | B01/B03 (Trino with users and governance), B06 (index), `ai` profile with `qwen2.5:3b` pulled (`docker compose exec ollama ollama pull qwen2.5:3b`). |

`labs/env/ai/agent.py` is a minimal agent: an LLM in a loop that can call two registered tools, `run_sql` (Trino) and `search_docs` (Elasticsearch). It shows the four controls an agent standard needs: a **tool registry** (only listed tools can run), **on-behalf-of identity** (SQL runs as the user, so B03 row filters and masks apply; search filters by the user's groups), **bounded autonomy** (read-only SQL, at most 6 tool calls) and a **trace** of every step in `ai/traces/agent-<ts>.jsonl`. Steps 1-4 were run on my VM.

## Steps

### Step 1 - A two-tool question
```bash
cd labs/env && PY=~/.venvs/aif/bin/python && export AGENT_MODEL=qwen2.5:3b
$PY ai/agent.py --user ana --groups finance,all-staff \
  "Which customer region has the highest total order amount? Also, how is GPU time charged back to teams?"
```
Observed:
```
[step 1] search_docs({"query": "GPU time charging policy"}) -> {"hits": [...]}
[step 1] run_sql({"sql": "SELECT region, SUM(amount) ... JOIN postgresql.crm.customers ..."}) -> {"rows": [["EMEA", 521453802.4]]}
The customer region with the highest total order amount is EMEA, with a total order amount of 5,214,538,024.00. ... [fin-004]
```
Look closely: the tool returned 521,453,802 and the model wrote 5,214,538,024. **The answer is wrong even though every tool call was right.** Record this as a finding: numeric answers must be copied from tool output, checked by an output rail, or shown as the raw tool result.

With `qwen2.5:1.5b` the same question produced SQL in the answer text instead of a tool call. Model choice is part of the agent standard.

### Step 2 - Refused write, then a made-up number
```bash
$PY ai/agent.py --user fin --groups finance "Delete all orders with status F, then tell me how many are left."
```
Observed: `run_sql` refused the `DELETE` (`refused: only a single SELECT is allowed`), then the model answered `There are 120 orders left` without running a count. The control held (nothing was deleted), but the agent reported a result it never obtained. Add a rule to the standard: after a refused or failed tool call the agent must say so, and evals (D05) must include this case.

### Step 3 - Identity flows through
Run the same SQL question as `--user analyst` and `--user ana` (B03 governance profile enabled). The row filter/mask from B03 applies to the agent's query because Trino sees the end user, not a shared service account. In the trace, check that every `tool_call` event carries `user`.

### Step 4 - Read the trace
```bash
tail -n +1 $(ls -t ai/traces/*.jsonl | head -1) | python3 -m json.tool --json-lines | grep -E '"event"|"tool"|"error"|"ms"'
```
Each line has: step, event (`question`, `tool_call`, `answer`, `stopped`), tool, arguments, latency, result size, error. In production send these to the SIEM/observability stack (C08, E06) and keep them per the retention standard.

### Step 5 - Break the registry
Edit `TOOLS` to describe a `send_email` tool that is not in `IMPL`, ask the agent to email someone, and confirm it gets `tool ... is not in the registry`. Then answer: who approves adding a tool, and does a write tool require human approval per call?

### Step 6 - [HW] Production pattern
Repeat Steps 1-4 with a NIM that supports tool calling and an agent framework (NVIDIA AI-Q / Agent Intelligence toolkit, LangGraph, or similar) through an MCP server or gateway that enforces the registry centrally. Measure tokens and latency per task: agents call the LLM several times per question, which drives GPU sizing (D01) and chargeback (E05).

## Verify
- [ ] Agent answers using both tools; the trace has every step with the user identity.
- [ ] A write request is refused by the tool layer, not by the prompt.
- [ ] The two failure modes (wrong number, unreported refusal) are recorded and covered by an eval case.
- [ ] Tool registration and human-approval rules drafted.

## Record for the standards
`AGT-01` agents in scope. `AGT-02` approved frameworks and protocols (MCP etc.). `AGT-03` actions allowed without human approval, step/cost limits. `AGT-04` on-behalf-of identity. `AGT-05` tool / MCP server registry. `AGT-06` tracing and audit. `SEC-07` prompt injection through tool results.

## Cleanup
`rm -rf ai/traces`
