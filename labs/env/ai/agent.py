"""Lab D06: a read-only agent that combines SQL (Trino, B05) and document search (B06) on behalf of one user.

  python ai/agent.py --user ana --groups finance,all-staff "Which region has the most customers, and how is GPU time charged back?"
- Tool registry: only the tools in TOOLS can be called; anything else is refused and logged.
- On-behalf-of identity: SQL runs as --user (Trino row filters/masks apply), search filters by --groups.
- Autonomy: read-only. SQL must be a single SELECT/WITH; at most MAX_STEPS tool calls.
- Every step (model output, tool call, arguments, result size, latency) is appended to traces/agent-<ts>.jsonl.
"""
import argparse, json, os, pathlib, re, sys, time, requests, trino
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "search"))
from rag_search import retrieve

HERE = pathlib.Path(__file__).parent
LLM = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
MODEL = os.environ.get("AGENT_MODEL", "qwen2.5:1.5b")
MAX_STEPS = 6
TOOLS = [
    {"type": "function", "function": {"name": "run_sql", "description":
        "Run one read-only Trino SELECT. Tables: postgresql.crm.customers(customer_id, name, region, segment, email), "
        "iceberg.curated.orders(order_id, customer_id, amount, order_date, status, channel). Always use full table names.",
        "parameters": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}}},
    {"type": "function", "function": {"name": "search_docs", "description": "Search internal policy and runbook documents.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]


def run_sql(a, sql):
    if not re.match(r"(?is)^\s*(select|with)\b", sql) or ";" in sql.strip().rstrip(";"):
        return {"error": "refused: only a single SELECT is allowed"}
    cur = trino.dbapi.connect(host="localhost", port=8080, user=a.user).cursor()
    try:
        cur.execute(sql.strip().rstrip(";")); return {"rows": cur.fetchmany(20)}
    except trino.exceptions.TrinoUserError as e:
        return {"error": e.message}


def search_docs(a, query):
    return {"hits": [{"doc_id": h["doc_id"], "title": h["title"], "text": h["text"]} for h in retrieve(query, a.groups.split(","))]}


IMPL = {"run_sql": run_sql, "search_docs": search_docs}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question"); ap.add_argument("--user", required=True); ap.add_argument("--groups", required=True)
    a = ap.parse_args()
    (HERE / "traces").mkdir(exist_ok=True)
    trace = open(HERE / "traces" / f"agent-{int(time.time())}.jsonl", "w")
    log = lambda **e: (trace.write(json.dumps(dict(e, ts=time.time(), user=a.user), default=str) + "\n"), trace.flush())
    msgs = [{"role": "system", "content": "You are a read-only analyst. Never show SQL to the user: call run_sql to get numbers and "
             "search_docs to get policy text, one tool call per sub-question, then answer briefly from the tool results. "
             "Cite document ids in square brackets."}, {"role": "user", "content": a.question}]
    log(step=0, event="question", question=a.question, groups=a.groups)
    for step in range(1, MAX_STEPS + 1):
        m = requests.post(LLM, json={"model": MODEL, "messages": msgs, "tools": TOOLS, "stream": False,
                                     "options": {"temperature": 0}}, timeout=300).json()["message"]
        msgs.append(m)
        if not m.get("tool_calls"):
            log(step=step, event="answer", text=m["content"]); print(m["content"]); break
        for c in m["tool_calls"]:
            name, args = c["function"]["name"], c["function"]["arguments"]
            t0 = time.time()
            out = IMPL[name](a, **args) if name in IMPL else {"error": f"tool {name} is not in the registry"}
            log(step=step, event="tool_call", tool=name, args=args, ms=int((time.time() - t0) * 1000),
                result_size=len(json.dumps(out, default=str)), error=out.get("error"))
            print(f"[step {step}] {name}({json.dumps(args)[:120]}) -> {json.dumps(out, default=str)[:160]}")
            msgs.append({"role": "tool", "content": json.dumps(out, default=str)})
    else:
        log(step=MAX_STEPS, event="stopped", reason="step limit"); print("stopped: step limit reached")
    print(f"trace: {trace.name}")
