"""Lab E05: monthly showback per tenant from GPU-hours, storage TB-month and tokens; flags unlabelled workloads.

  python ops/showback.py                                   # GPU usage from ops/usage-sample.csv
  python ops/showback.py --gpu-usage <export.csv>          # real export from Kueue/Slurm/Run:ai/DCGM
Storage is measured live from the lab S3 buckets (bucket -> tenant map below); tokens from the D06 agent traces.
"""
import argparse, collections, csv, json, os, pathlib, boto3, yaml

ENV = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.strip().split("=", 1) for l in open(ENV / ".env") if "=" in l and not l.startswith("#"))
BUCKET_TENANT = {"bu-finance": "team-c", "bu-research": "team-a", "checkpoints": "team-a", "model-registry": "platform",
                 "documents": "team-c", "warehouse": "platform"}
ap = argparse.ArgumentParser()
ap.add_argument("--gpu-usage", default=str(ENV / "ops/usage-sample.csv")); ap.add_argument("--tokens-per-tenant", default="{}")
a = ap.parse_args()
card = yaml.safe_load(open(ENV / "ops/rates.yaml")); r = card["rates"]
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_URL", "http://localhost:8333"), region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])

bill = collections.defaultdict(lambda: collections.Counter())
unlabelled = []
for row in csv.DictReader(open(a.gpu_usage)):
    gh = float(row["gpus"]) * float(row["hours"])
    missing = [l for l in card["required_labels"] if not row.get(l)]
    tenant = row["team"] if not missing else "UNALLOCATED"
    if missing: unlabelled.append((row["namespace"], row["workload"], gh, missing))
    bill[tenant]["gpu_hours"] += gh
for b, t in BUCKET_TENANT.items():
    size = sum(o["Size"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=b) for o in p.get("Contents", []))
    bill[t]["tb_month"] += size / 1e12
for t, n in json.loads(a.tokens_per_tenant).items():
    bill[t]["mtok"] += n / 1e6

print(f"{'tenant':12} {'GPU-h':>8} {'TB-month':>10} {'Mtok':>7} {'cost ' + card['currency']:>11}")
total = 0
for t in sorted(bill, key=lambda t: (t == "UNALLOCATED", t)):
    c = bill[t]; cost = c["gpu_hours"] * r["gpu_hour"] + c["tb_month"] * r["storage_tb_month"] + c["mtok"] * r["mtok"]; total += cost
    print(f"{t:12} {c['gpu_hours']:8.1f} {c['tb_month']:10.6f} {c['mtok']:7.2f} {cost:11.2f}")
print(f"{'total':12} {'':8} {'':10} {'':7} {total:11.2f}")
if unlabelled:
    print("\nUnlabelled workloads (charged to UNALLOCATED until fixed):")
    for ns, w, gh, miss in unlabelled: print(f"  {ns}/{w}: {gh:.1f} GPU-h, missing {', '.join(miss)}")
    total_gh = sum(c["gpu_hours"] for c in bill.values())
    if total_gh: print(f"  {sum(x[2] for x in unlabelled) / total_gh:.0%} of GPU-hours are unallocated")
