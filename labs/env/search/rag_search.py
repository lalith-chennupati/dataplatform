"""Lab B06: permission-aware hybrid search on the Data Search Engine stand-in (Elasticsearch + Ollama embeddings).

  python rag_search.py ingest                      # chunk + embed + index corpus.jsonl
  python rag_search.py search "query" --groups finance,all-staff [--mode bm25|knn|hybrid]
  python rag_search.py eval --groups <all groups>  # recall@3 and MRR per mode on qrels.jsonl
"""
import argparse, json, os, pathlib, requests
from elasticsearch import Elasticsearch

HERE = pathlib.Path(__file__).parent
ES = Elasticsearch(os.environ.get("ES_URL", "http://localhost:9200"))
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
INDEX = "docs-chunks"


def embed(text):
    r = requests.post(f"{OLLAMA}/api/embeddings", json={"model": EMBED_MODEL, "prompt": text}, timeout=120)
    r.raise_for_status()
    return r.json()["embedding"]


def chunks(text, size=40, overlap=10):
    words = text.split()
    for start in range(0, max(len(words) - overlap, 1), size - overlap):
        yield " ".join(words[start:start + size])


def ingest(_):
    docs = []
    for line in open(HERE / "corpus.jsonl"):
        d = json.loads(line)
        for i, c in enumerate(chunks(d["text"])):
            docs.append((f"{d['id']}#{i}", {"doc_id": d["id"], "title": d["title"], "path": d["path"], "acl": d["acl"],
                                            "text": c, "vector": embed(f"{d['title']}. {c}")}))
    # embed everything first so a failed embedding run leaves the existing index intact
    ES.indices.delete(index=INDEX, ignore_unavailable=True)
    ES.indices.create(index=INDEX, mappings={"properties": {
        "doc_id": {"type": "keyword"}, "title": {"type": "text"}, "path": {"type": "keyword"},
        "acl": {"type": "keyword"}, "text": {"type": "text"},
        "vector": {"type": "dense_vector", "dims": len(docs[0][1]["vector"]), "index": True, "similarity": "cosine"}}})
    for doc_id, doc in docs:
        ES.index(index=INDEX, id=doc_id, document=doc)
    ES.indices.refresh(index=INDEX)
    print(f"indexed {len(docs)} chunks")


def search(q, groups, mode="hybrid", k=3):
    acl = {"terms": {"acl": groups}}
    body = {"size": k * 3, "_source": ["doc_id", "title", "acl"]}
    if mode in ("bm25", "hybrid"):
        body["query"] = {"bool": {"must": {"multi_match": {"query": q, "fields": ["title^2", "text"]}}, "filter": acl, "boost": 0.2}}
    if mode in ("knn", "hybrid"):
        body["knn"] = {"field": "vector", "query_vector": embed(q), "k": k * 3, "num_candidates": 50, "filter": acl}
    hits, seen = [], set()
    for h in ES.search(index=INDEX, **body)["hits"]["hits"]:
        if h["_source"]["doc_id"] not in seen:
            seen.add(h["_source"]["doc_id"]); hits.append((round(h["_score"], 3), h["_source"]["doc_id"], h["_source"]["title"]))
    return hits[:k]


def cmd_search(a):
    for hit in search(a.query, a.groups.split(","), a.mode):
        print(*hit, sep="\t")


def cmd_eval(a):
    qrels = [json.loads(l) for l in open(HERE / "qrels.jsonl")]
    for mode in ("bm25", "knn", "hybrid"):
        rec = mrr = 0.0
        for r in qrels:
            ids = [h[1] for h in search(r["q"], a.groups.split(","), mode)]
            if r["relevant"] in ids:
                rec += 1; mrr += 1 / (ids.index(r["relevant"]) + 1)
        print(f"{mode:7s} recall@3={rec/len(qrels):.2f} MRR={mrr/len(qrels):.2f}")


p = argparse.ArgumentParser()
sub = p.add_subparsers(required=True)
sub.add_parser("ingest").set_defaults(f=ingest)
s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--groups", required=True)
s.add_argument("--mode", default="hybrid", choices=["bm25", "knn", "hybrid"]); s.set_defaults(f=cmd_search)
e = sub.add_parser("eval"); e.add_argument("--groups", required=True); e.set_defaults(f=cmd_eval)
args = p.parse_args(); args.f(args)
