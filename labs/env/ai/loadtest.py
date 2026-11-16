"""Labs D01/D02: load-test any OpenAI-compatible chat endpoint (NIM, Dell Enterprise Hub/TGI, vLLM, Ollama).

  python ai/loadtest.py --url http://localhost:11434/v1 --model qwen2.5:0.5b --concurrency 1,4 --requests 16
Reports per concurrency level: requests/s, output tokens/s, p50/p95 end-to-end latency and p95 time-to-first-token.
"""
import argparse, json, statistics, time, requests
from concurrent.futures import ThreadPoolExecutor

PROMPTS = ["Summarise the benefits of a data lakehouse in two sentences.",
           "List three risks of sharing GPUs between teams.",
           "Explain RDMA to a storage administrator in one paragraph.",
           "Write a short checklist for onboarding a new AI tenant."]


def one(a, i):
    body = {"model": a.model, "messages": [{"role": "user", "content": PROMPTS[i % len(PROMPTS)]}],
            "max_tokens": a.max_tokens, "stream": True, "stream_options": {"include_usage": True}}
    hdr = {"Authorization": f"Bearer {a.api_key}"} if a.api_key else {}
    t0, ttft, chunks, usage = time.perf_counter(), None, 0, None
    with requests.post(f"{a.url}/chat/completions", json=body, headers=hdr, stream=True, timeout=600) as r:
        r.raise_for_status()
        for line in r.iter_lines(chunk_size=1):  # default 512-byte buffering would delay the first token
            if not line.startswith(b"data: ") or line == b"data: [DONE]":
                continue
            d = json.loads(line[6:])
            if d.get("usage"):
                usage = d["usage"]
            if d.get("choices") and d["choices"][0].get("delta", {}).get("content"):
                ttft = ttft or time.perf_counter() - t0
                chunks += 1
    tokens = (usage or {}).get("completion_tokens") or chunks
    return time.perf_counter() - t0, ttft or 0, tokens


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:11434/v1")
    ap.add_argument("--model", default="qwen2.5:0.5b")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--concurrency", default="1,4")
    ap.add_argument("--requests", type=int, default=16)
    ap.add_argument("--max-tokens", type=int, default=128)
    a = ap.parse_args()
    one(a, 0)  # warm-up: loads the model
    print(f"{'conc':>4} {'req/s':>6} {'tok/s':>7} {'p50 s':>6} {'p95 s':>6} {'p95 ttft s':>10}")
    for c in map(int, a.concurrency.split(",")):
        t0 = time.perf_counter()
        with ThreadPoolExecutor(c) as ex:
            res = list(ex.map(lambda i: one(a, i), range(max(a.requests, c))))
        wall = time.perf_counter() - t0
        lat, ttft, tok = zip(*res)
        print(f"{c:>4} {len(res) / wall:6.2f} {sum(tok) / wall:7.1f} {statistics.median(lat):6.2f} {pct(lat, 95):6.2f} {pct(ttft, 95):10.2f}")
