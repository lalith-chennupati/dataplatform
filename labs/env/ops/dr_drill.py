"""Lab E04 (SIM): DR drill with asynchronous replication, measured RPO and RTO.

  python ops/dr_drill.py --interval 15 --run 40
A writer adds one order object per second to s3://dr-primary/orders/. A replicator copies new objects to
s3://dr-secondary/ every --interval seconds (the SyncIQ policy schedule). After --run seconds the primary "fails":
the drill stops writes, promotes the secondary, checks that the app can read from it and reports
  RPO = age of the newest object that did NOT reach the secondary (data loss window)
  RTO = time from failure to the first successful read on the promoted site
Then it fails back (reverse sync of anything written on the secondary while promoted).
SIM stand-in for SyncIQ failover/failback; the measurements and runbook order are what carry over.
"""
import argparse, os, pathlib, threading, time, boto3

ENV = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.strip().split("=", 1) for l in open(ENV / ".env") if "=" in l and not l.startswith("#"))
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_URL", "http://localhost:8333"), region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])
P, S = "dr-primary", "dr-secondary"


def keys(b):
    return {o["Key"]: o for p in s3.get_paginator("list_objects_v2").paginate(Bucket=b) for o in p.get("Contents", [])}


def sync(src, dst):
    have = keys(dst); n = 0
    for k in keys(src):
        if k not in have: s3.copy_object(Bucket=dst, Key=k, CopySource={"Bucket": src, "Key": k}); n += 1
    return n


def reset():
    for b in (P, S):
        try: s3.create_bucket(Bucket=b)
        except s3.exceptions.ClientError: pass
        for k in keys(b): s3.delete_object(Bucket=b, Key=k)


ap = argparse.ArgumentParser()
ap.add_argument("--interval", type=float, default=15); ap.add_argument("--run", type=float, default=40)
a = ap.parse_args()
reset()
failed, written = threading.Event(), {}


def writer():
    i = 0
    while not failed.is_set():
        k = f"orders/{i:06d}.json"; s3.put_object(Bucket=P, Key=k, Body=f'{{"order": {i}}}'.encode()); written[k] = time.time(); i += 1
        failed.wait(1)


def replicator():
    while not failed.wait(a.interval):
        print(f"  [{time.strftime('%H:%M:%S')}] replication cycle copied {sync(P, S)} objects")


threads = [threading.Thread(target=writer), threading.Thread(target=replicator)]
for t in threads: t.start()
print(f"writing to {P}, replicating to {S} every {a.interval:.0f}s, primary fails in {a.run:.0f}s")
time.sleep(a.run)
failed.set(); t_fail = time.time()
for t in threads: t.join()
print(f"[{time.strftime('%H:%M:%S')}] PRIMARY SITE FAILED")

# Failover runbook: 1) declare disaster 2) break replication / make secondary writable 3) repoint app 4) verify
sec = keys(S)
lost = sorted(k for k in written if k not in sec)
rpo = t_fail - min(written[k] for k in lost) if lost else 0.0
app_bucket = S  # step 3: in production a DNS / config change (GitOps commit) points the app at the DR endpoint
newest = max(sec) if sec else None
body = s3.get_object(Bucket=app_bucket, Key=newest)["Body"].read() if newest else b""
rto = time.time() - t_fail
print(f"failover: app now reads {app_bucket}; newest replicated object {newest} = {body.decode()}")
print(f"RPO {rpo:.1f}s ({len(lost)} of {len(written)} orders not replicated)   RTO {rto:.1f}s (automation only, excludes decision time)")

# Work continues on the DR site, then fail back
for i in range(3): s3.put_object(Bucket=S, Key=f"orders/dr-{i:03d}.json", Body=b'{"written_on": "dr"}')
print(f"failback: reverse sync copied {sync(S, P)} objects written during DR to {P}; "
      f"{len(lost)} un-replicated orders on {P} must be reconciled by the application owner")
