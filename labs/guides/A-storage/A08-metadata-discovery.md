# A08 - Discover AI-ready data with metadata

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| DEMO / HW (MetadataIQ needs a supported OneFS release); SIM fallback provided | 3 h | DAT, STO | A01; Elasticsearch from L01 (core profile) |

**PowerScale MetadataIQ** indexes OneFS file-system metadata into an external search database, so data teams can find datasets by path, owner, size, type, age and custom tags. Availability and setup depend on the OneFS release. Follow the MetadataIQ guide for your version in the DEMO/HW path. The SIM fallback builds the same searchable index with a small crawler so you can practise the discovery workflow.

## Steps

### Step 1 - [DEMO/HW] Configure MetadataIQ
1. Confirm the OneFS version supports MetadataIQ (`isi version`), and read the release notes for the supported target databases (Elasticsearch is the reference target).
2. Deploy or identify the target search cluster. In the lab, the L01 Elasticsearch on `:9200` can be the target if it is reachable from the cluster.
3. Configure MetadataIQ on OneFS: target endpoint, credentials, the paths to index (e.g. `/ifs/data`) and the schedule. Run an initial full scan.
4. Confirm the index exists: `curl -s $ES:9200/_cat/indices?v | grep -i metadata`.

### Step 2 - [SIM] Build the equivalent index with a crawler
Mount any share (PowerScale export from A01, or a local directory full of sample files), then:
```bash
cd labs/env && . ~/.venvs/aif/bin/activate
python3 - <<'PY'
import os, pwd, time, mimetypes
from elasticsearch import Elasticsearch, helpers
ROOT = os.environ.get("ROOT", "/mnt/ps-ai")           # or any directory
es = Elasticsearch("http://localhost:9200")
es.indices.create(index="fs-metadata", ignore=400, mappings={"properties": {
    "path": {"type": "keyword"}, "ext": {"type": "keyword"}, "owner": {"type": "keyword"},
    "size": {"type": "long"}, "mtime": {"type": "date", "format": "epoch_second"}, "mime": {"type": "keyword"},
    "tags": {"type": "keyword"}}})
def docs():
    for d, _, files in os.walk(ROOT):
        for f in files:
            p = os.path.join(d, f); st = os.stat(p)
            try: owner = pwd.getpwuid(st.st_uid).pw_name
            except KeyError: owner = str(st.st_uid)
            yield {"_index": "fs-metadata", "_id": p, "_source": {
                "path": p, "ext": os.path.splitext(f)[1].lower(), "owner": owner, "size": st.st_size,
                "mtime": int(st.st_mtime), "mime": mimetypes.guess_type(f)[0] or "unknown",
                "tags": [x for x in p.split("/") if x.startswith("bu-")]}}
print(helpers.bulk(es, docs()))
PY
```

### Step 3 - Discovery queries
```bash
# All PDFs changed in the last 90 days, newest first
curl -s localhost:9200/fs-metadata/_search -H 'Content-Type: application/json' -d '{
  "size": 20, "sort": [{"mtime": "desc"}],
  "query": {"bool": {"filter": [{"term": {"ext": ".pdf"}}, {"range": {"mtime": {"gte": "now-90d/d"}}}]}}}' | python3 -m json.tool | grep '"path"'
# Capacity by file type
curl -s localhost:9200/fs-metadata/_search -H 'Content-Type: application/json' -d '{
  "size": 0, "aggs": {"by_ext": {"terms": {"field": "ext", "size": 10}, "aggs": {"bytes": {"sum": {"field": "size"}}}}}}' | python3 -m json.tool
```

### Step 4 - Tag datasets as "AI-ready"
Agree a tag vocabulary with the data owners, e.g. `ai-ready`, `contains-pii`, `owner:<team>`, `class:confidential`. Apply the tags. With MetadataIQ use its custom-attribute support. In SIM, use an update-by-query:
```bash
curl -s -XPOST 'localhost:9200/fs-metadata/_update_by_query' -H 'Content-Type: application/json' -d '{
  "script": {"source": "ctx._source.tags.add(\"ai-ready\")"},
  "query": {"prefix": {"path": "/mnt/ps-ai/datasets"}}}'
```

### Step 5 - Hand off to RAG ingestion
Export the `ai-ready` file list as the input manifest for D03:
```bash
curl -s localhost:9200/fs-metadata/_search -H 'Content-Type: application/json' \
  -d '{"size":1000,"_source":["path"],"query":{"term":{"tags":"ai-ready"}}}' \
  | python3 -c "import sys,json; [print(h['_source']['path']) for h in json.load(sys.stdin)['hits']['hits']]" > ../evidence/a08-manifest.txt
wc -l ../evidence/a08-manifest.txt
```

## Verify
- [ ] The index contains every file under the scanned path (compare with `find $ROOT -type f | wc -l`).
- [ ] Discovery queries answer "what, where, whose, how big, how old" without anyone walking the tree by hand.
- [ ] An `ai-ready` manifest is produced for D03.

## Record for the standards
`DAT-06` catalog of record and mandatory metadata fields. `STO-10` metadata indexing. `DAT-01` classification tags.

## Cleanup
`curl -XDELETE localhost:9200/fs-metadata`
