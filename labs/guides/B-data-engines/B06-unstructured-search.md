# B06 - Unstructured search with the Data Search Engine

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Elasticsearch 8.15 + Ollama embeddings) / DEMO (Dell Data Search Engine) | 3 h | RAG, SEC, DAT | L01 with `core ai` profiles and `nomic-embed-text` pulled. Python venv from L01 Step 7. |

The Dell Data Search Engine is Elastic-based. The index mappings and queries below are standard Elasticsearch 8.x. On DEMO, use the engine's PowerScale connector instead of Step 2, and native document-level security instead of the application filter in Step 5.

## Prerequisites
```bash
cd labs/env && make up PROFILES="core ai"
docker compose exec ollama ollama pull nomic-embed-text
. ~/.venvs/aif/bin/activate && pip install elasticsearch==8.15.1 requests
```

## Steps

### Step 1 - Look at the sample corpus
`labs/env/search/corpus.jsonl` holds 12 documents from three "shares" (finance, research, platform). Each has an `acl` list, which is the set of groups allowed to read the file. The ACL is what a PowerScale connector would copy from the file's ACL. Two documents are restricted to `*-leadership` groups.
```bash
python3 -c "import json;[print(d['id'], d['acl'], d['title']) for d in map(json.loads, open('search/corpus.jsonl'))]"
```
[DEMO] Instead, point the connector at an SMB share from A01/A02 and make sure it syncs file ACLs (permissions) as well as content.

### Step 2 - Chunk, embed and index
```bash
python search/rag_search.py ingest          # indexed N chunks
curl -s localhost:9200/docs-chunks/_mapping | python3 -m json.tool | grep -A3 '"vector"'   # dense_vector, 768 dims, cosine
```
Read `ingest()` in `search/rag_search.py`. Each chunk keeps `doc_id`, `path` and `acl` from its parent document. The chunk size is 40 words with a 10-word overlap. Try 100/20 for longer documents.

### Step 3 - Compare BM25, vector and hybrid search
```bash
G=finance,research,platform,all-staff
for m in bm25 knn hybrid; do echo "== $m"; python search/rag_search.py search "steps to swap a broken GPU server" --groups $G --mode $m; done
```
BM25 needs the words to match ("replace" vs. "swap"). Vector search matches the meaning. Hybrid combines both scores in one request (`query` + `knn`). On a licence that includes it, try reciprocal rank fusion (`retriever: {rrf: ...}`) as well.

### Step 4 - Measure relevance
```bash
python search/rag_search.py eval --groups finance,finance-leadership,research,research-leadership,platform,security,all-staff
```
Expected output (SIM run, recorded by Devin): `bm25 recall@3=1.00 MRR=0.88`, `knn recall@3=1.00 MRR=1.00`, `hybrid recall@3=1.00 MRR=0.90`.
Add 10 questions from your own domain to `search/qrels.jsonl` and run the evaluation again. The tiny corpus makes every mode look good. Your own documents will separate them.

### Step 5 - Permission-aware retrieval
```bash
python search/rag_search.py search "what is the Q3 revenue forecast" --groups finance,all-staff
python search/rag_search.py search "what is the Q3 revenue forecast" --groups finance,finance-leadership,all-staff
python search/rag_search.py search "unreleased model benchmark score" --groups research,all-staff
```
Expected: `fin-003` only appears for the leadership group. `res-004` never appears for `research`.
The filter is applied **inside** both the BM25 query and the kNN search (`knn.filter`). That matters: filtering after the kNN search would return fewer than k hits and can leak document existence through scores.

### Step 6 - [DEMO] Native document-level security
With Elastic security enabled, create a role per group with a DLS query, and search as a user who has that role:
```bash
curl -u elastic:$PW -XPUT "$ES/_security/role/finance_reader" -H 'Content-Type: application/json' -d '{
  "indices": [{"names": ["docs-chunks"], "privileges": ["read"],
               "query": {"terms": {"acl": ["finance", "all-staff"]}}}]}'
curl -u elastic:$PW -XPUT "$ES/_security/user/fiona" -H 'Content-Type: application/json' -d '{"password":"Lab#2026x","roles":["finance_reader"]}'
curl -u fiona:Lab#2026x "$ES/docs-chunks/_search?q=forecast" | grep -c fin-003        # 0
```
For per-user ACLs, use a templated role query (`{{_user.metadata.groups}}`) or the connector's built-in document-level security sync.

### Step 7 - Keep the index in sync
Change one document's `acl` in `corpus.jsonl` (e.g. remove `all-staff` from `ops-004`) and re-run `ingest`. Then search as `all-staff`. Record how long a permission change takes to reach the index in your DEMO connector (the sync schedule). That delay is your exposure window.

## Verify
- [ ] Hybrid search returns relevant results for paraphrased questions.
- [ ] Recall@3 and MRR are recorded per mode, including on your own questions.
- [ ] Restricted documents never appear for users without access (`RAG-03`).
- [ ] The ACL sync delay is recorded.

## Record for the standards
`RAG-03` permission-aware retrieval (mandatory filter in every retrieval call). `RAG-02` retrieval reference design (hybrid). `RAG-04` embedding model and re-index policy. `RAG-05` chunking rules. `RAG-07` ACL and deletion propagation delay. `RAG-08` relevance metrics and thresholds.

## Cleanup
`curl -XDELETE localhost:9200/docs-chunks`
