"""Lab E06: build an auditor-ready evidence pack for one AI use case (the D03-D07 finance assistant).

  python ops/evidence_pack.py --model d04-lora-adapter --out ../evidence/e06-pack.zip
Collects: model registry record (versions, aliases, gate results, lineage), dataset hash, RAG corpus inventory with
ACLs, guardrail/red-team results, agent traces, zero-trust scan, Git revision. Writes manifest.json with a sha256 per
file and the questionnaire IDs each file is evidence for. Missing items are listed as gaps, not silently skipped.
"""
import argparse, hashlib, io, json, os, pathlib, subprocess, sys, time, zipfile
from mlflow.tracking import MlflowClient

ENV = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="d04-lora-adapter"); ap.add_argument("--out", default=str(ENV.parent / "evidence/e06-pack.zip"))
a = ap.parse_args()
files, gaps = {}, []


def add(name, data, ids):
    data = data if isinstance(data, bytes) else data.encode()
    files[name] = (data, ids)


def run(cmd):
    r = subprocess.run(cmd, cwd=ENV, capture_output=True, text=True, env=os.environ | {"PYTHONWARNINGS": "ignore"})
    return r.returncode, r.stdout + r.stderr


try:
    c = MlflowClient(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    rm = c.get_registered_model(a.model)
    vers = []
    for v in c.search_model_versions(f"name='{a.model}'"):
        run_ = c.get_run(v.run_id)
        vers.append({"version": v.version, "created": v.creation_timestamp, "source": v.source, "run_id": v.run_id,
                     "tags": v.tags, "params": run_.data.params, "metrics": run_.data.metrics})
    add("model/registry.json", json.dumps({"name": a.model, "aliases": rm.aliases, "versions": vers}, indent=1, default=str),
        ["GOV-06", "MLO-03", "MLO-04", "MLO-12"])
except Exception as e:
    gaps.append(f"model registry: {e.__class__.__name__}: {e}"[:200])

ft = ENV / "ai/finetune.jsonl"
add("data/finetune.sha256", f"{hashlib.sha256(ft.read_bytes()).hexdigest()}  ai/finetune.jsonl\n", ["MLO-10", "PRV-05"])
corpus = [json.loads(l) for l in open(ENV / "search/corpus.jsonl")]
add("data/rag-corpus-inventory.json", json.dumps([{k: d[k] for k in ("id", "title", "path", "acl")} for d in corpus], indent=1),
    ["RAG-03", "PRV-02", "PRV-05"])

rc, out = run([sys.executable, "ai/guard_eval.py"])
add("eval/guardrails-redteam.txt", out, ["MLO-07", "MLO-09", "SEC-06", "SEC-11"])
if rc: gaps.append("guardrail release gate is failing")

traces = sorted((ENV / "ai/traces").glob("*.jsonl")) if (ENV / "ai/traces").exists() else []
for t in traces[-5:]: add(f"traces/{t.name}", t.read_bytes(), ["AGT-06", "PRV-05", "SEC-10"])
if not traces: gaps.append("no agent traces (run D06 first)")

rc, out = run([sys.executable, "ops/zt_scan.py"])
add("security/zt-scan.txt", out, ["SEC-01", "SEC-02", "SEC-04", "SEC-05"])
if rc: gaps.append("zero-trust scan has failing checks (see security/zt-scan.txt)")

add("source/git-revision.txt", run(["git", "log", "-1", "--format=%H %ad %s"])[1], ["MLO-04"])

manifest = {"use_case": "finance assistant (D03-D07)", "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gaps": gaps,
            "files": {n: {"sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d), "evidence_for": ids} for n, (d, ids) in files.items()}}
pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
    for n, (d, _) in files.items(): z.writestr(n, d)
    z.writestr("manifest.json", json.dumps(manifest, indent=1))
print(f"{a.out}: {len(files)} files, {len(gaps)} gaps")
for g in gaps: print("  GAP:", g)
covered = sorted({i for _, ids in files.values() for i in ids})
print("evidence for:", " ".join(covered))
