# D03 - End-to-end RAG on the AI Data Platform

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Elasticsearch + Ollama) / DEMO-HW (PowerScale + Data Search Engine + NIM, NVIDIA RAG blueprint) | 4 h | RAG, SEC, PRV, STO | B06 done (index built). `ai` profile with `nomic-embed-text` and `qwen2.5:1.5b` pulled. |

The pipeline: documents on PowerScale -> discovery (A08) -> parse and chunk -> embed -> index with each chunk's ACL -> retrieve **with the caller's groups as a filter** -> LLM answers only from the retrieved chunks and cites them. `search/rag_answer.py` adds the generation step to B06's `rag_search.py`. The LLM endpoint is any OpenAI-compatible API: Ollama in SIM, a NIM (D01) in HW (`LLM_URL=http://<nim>:8000/v1 LLM_MODEL=meta/llama-3.1-8b-instruct`). Steps 1-5 were run on my VM.

## Steps

### Step 1 - Index and a first answer
```bash
cd labs/env && PY=~/.venvs/aif/bin/python
$PY search/rag_search.py ingest
$PY search/rag_answer.py "how much can I spend on a hotel" --groups finance,all-staff
```
Expected (observed):
```
According to the source [fin-001], hotel costs are capped at 250 USD per night in tier-one cities.
retrieved: res-002 (...), fin-001 (/ifs/bu-finance/policies/travel.md), ops-004 (...)
cited: fin-001
```
The script exits non-zero if the answer cites a document that was not retrieved, or gives an answer with no citation.

### Step 2 - Restricted documents never leak
```bash
$PY search/rag_answer.py "what is the Q3 revenue forecast" --groups finance,all-staff        # I don't know based on the documents you can access.
$PY search/rag_answer.py "what is the Q3 revenue forecast" --groups finance-leadership       # 412 million USD ... [fin-003]
```
`fin-003` is filtered out inside the Elasticsearch query for the first caller, so the LLM never sees it. Never rely on the prompt ("do not reveal...") for access control. Repeat for `res-004` with `research` vs `research-leadership`. Save the outputs as evidence.

### Step 3 - Deletion propagation
```bash
$PY search/rag_search.py delete fin-001                                              # deleted N chunks of fin-001
$PY search/rag_search.py search "hotel spend per night" --groups finance,all-staff   # fin-001 gone
$PY search/rag_search.py ingest                                                      # restore
```
In production the trigger is the source: a file deleted or moved on PowerScale (A08 MetadataIQ change list, or OneFS audit events) must remove its chunks within the agreed SLA. Write down the mechanism and the SLA (`RAG-07`, `PRV-04`).

### Step 4 - ACL change propagation
Edit `search/corpus.jsonl`: remove `all-staff` from `ops-004`, re-run `ingest`, and query as `all-staff`. Record how the real connector learns about ACL changes (OneFS ACL change -> re-index of that document's metadata) and how long it takes. That delay is the exposure window.

### Step 5 - Evaluate
Write 10 questions with the expected document and expected fact. Run each through `rag_answer.py` and score: retrieval hit (expected doc retrieved), citation correct, answer correct, refusal correct for out-of-scope questions. B06's `eval` gives retrieval recall/MRR; D05 adds groundedness and red-team tests.

### Step 6 - [DEMO/HW] Production pipeline
With the NVIDIA RAG blueprint (or your own): ingestion service reading from the PowerScale share, NeMo Retriever embedding NIM, vector store (Data Search Engine / Elasticsearch or Milvus with GPU indexing, B07), LLM NIM. Repeat Steps 1-4 against it with real department documents and real AD groups. Record ingestion throughput (docs/hour) and re-index time for the whole corpus.

## Verify
- [ ] Answers cite retrieved sources; uncited answers fail the script.
- [ ] Restricted documents are not retrievable by users outside their ACL.
- [ ] Deletion and ACL changes reach the index; the SLA is written down.
- [ ] A 10-question evaluation is recorded.

## Record for the standards
`RAG-03` permission-aware retrieval. `RAG-05` chunking, metadata and citation rules. `RAG-07` freshness and deletion. `RAG-08` evaluation. `PRV-04` data-subject deletion through embeddings. `PRV-02` which data classes may be indexed.

## Cleanup
`$PY search/rag_search.py ingest` restores the original index after Steps 3-4 (revert `corpus.jsonl` first: `git checkout search/corpus.jsonl`).
