"""Lab D03: answer a question from the documents the caller may read, with citations.

  python search/rag_answer.py "how much can I spend on a hotel" --groups finance,all-staff
Retrieval is ACL-filtered (rag_search.retrieve). The LLM (Ollama OpenAI-compatible API, or a NIM via LLM_URL)
sees only those chunks. Any citation that is not one of the retrieved documents is reported as a failure.
"""
import argparse, os, re, sys, requests
from rag_search import retrieve

LLM_URL = os.environ.get("LLM_URL", os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:1.5b")
SYSTEM = ("Answer only from the sources below. Cite every fact with the source id in square brackets, e.g. [fin-001]. "
          "If the sources do not contain the answer, reply exactly: I don't know based on the documents you can access.")


def answer(q, groups, k=3):
    hits = retrieve(q, groups, k=k)
    ctx = "\n\n".join(f"[{h['doc_id']}] {h['title']} ({h['path']})\n{h['text']}" for h in hits)
    r = requests.post(f"{LLM_URL}/chat/completions", timeout=300, json={
        "model": LLM_MODEL, "temperature": 0, "max_tokens": 200,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Sources:\n{ctx}\n\nQuestion: {q}\nEnd every sentence of your answer with the id of its source in square brackets."}]})
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    cited = set(re.findall(r"\[([a-z]+-\d{3})\]", text))
    return text, hits, cited, cited - {h["doc_id"] for h in hits}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question"); ap.add_argument("--groups", required=True); ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()
    text, hits, cited, bad = answer(a.question, a.groups.split(","), a.k)
    print(text)
    print("\nretrieved:", ", ".join(f"{h['doc_id']} ({h['path']})" for h in hits))
    print("cited:", ", ".join(sorted(cited)) or "none")
    if bad:
        sys.exit(f"FAIL: cited documents that were not retrieved: {sorted(bad)}")
    if not cited and not text.startswith("I don't know"):
        sys.exit("FAIL: answer has no citations")
