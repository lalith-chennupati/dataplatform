"""Lab D07: promotion gate for registered models. Runs the evaluation gate, records the result on the model version,
and moves the `champion` alias only if the gate passes. `--rollback` points `champion` back to the previous version.

  python ai/promote.py --name d04-lora-adapter --version 2
  python ai/promote.py --name d04-lora-adapter --rollback
"""
import argparse, json, os, pathlib, subprocess, sys
from mlflow.tracking import MlflowClient

HERE = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True); ap.add_argument("--version"); ap.add_argument("--rollback", action="store_true")
ap.add_argument("--gate", default=f"{sys.executable} {HERE / 'guard_eval.py'}", help="command whose exit code is the gate")
a = ap.parse_args()
c = MlflowClient(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))


def champion():
    try: return c.get_model_version_by_alias(a.name, "champion").version
    except Exception: return None


if a.rollback:
    prev = c.get_registered_model(a.name).aliases.get("previous-champion")
    if not prev: sys.exit("no previous-champion alias to roll back to")
    cur = champion()
    c.set_registered_model_alias(a.name, "champion", prev)
    if cur: c.set_registered_model_alias(a.name, "previous-champion", cur)
    print(f"rolled back {a.name}: champion v{cur} -> v{prev}"); sys.exit(0)

v = a.version or max(int(m.version) for m in c.search_model_versions(f"name='{a.name}'"))
c.set_registered_model_alias(a.name, "candidate", v)
r = subprocess.run(a.gate.split(), capture_output=True, text=True)
score = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
c.set_model_version_tag(a.name, v, "gate_result", "pass" if r.returncode == 0 else "fail")
c.set_model_version_tag(a.name, v, "gate_score", score[:500])
if r.returncode != 0:
    print(f"{a.name} v{v} FAILED the gate, champion stays v{champion()}: {score}"); sys.exit(1)
cur = champion()
if cur and str(cur) != str(v): c.set_registered_model_alias(a.name, "previous-champion", cur)
c.set_registered_model_alias(a.name, "champion", v)
print(f"{a.name} v{v} passed the gate and is champion (previous v{cur}): {score}")
