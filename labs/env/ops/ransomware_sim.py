"""Lab E02 (SIM): simulate mass encryption of a versioned S3 share, detect it, restore the last clean versions, time it.

  python ops/ransomware_sim.py seed       # 200 documents in s3://e02-share (versioning on)
  python ops/ransomware_sim.py attack     # overwrite every document with random bytes (the "encryption")
  python ops/ransomware_sim.py detect     # entropy scan: share of objects that look encrypted
  python ops/ransomware_sim.py recover    # restore the newest low-entropy version of every object, print RTO
  python ops/ransomware_sim.py verify     # compare every object with the seed hashes
Real attackers also delete versions; only object lock / SmartLock WORM or an isolated vault (PowerProtect Cyber
Recovery) stops that. Run A09 Step 5 to see a locked version survive a delete.
"""
import collections, hashlib, json, math, os, pathlib, sys, time, boto3
from concurrent.futures import ThreadPoolExecutor

ENV = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.strip().split("=", 1) for l in open(ENV / ".env") if "=" in l and not l.startswith("#"))
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_URL", "http://localhost:8333"), region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])
B, N, STATE = "e02-share", 200, ENV / "ops" / ".e02-seed.json"


def entropy(b):
    if not b: return 0.0
    c = collections.Counter(b)
    return -sum(n / len(b) * math.log2(n / len(b)) for n in c.values())


def keys():
    return [f"share/doc-{i:04d}.txt" for i in range(N)]


def body(i):
    return (f"Document {i}\nOwner: finance\n" + "Quarterly figures and commentary for the close process. " * 40).encode()


def seed():
    try: s3.create_bucket(Bucket=B)
    except s3.exceptions.ClientError: pass
    s3.put_bucket_versioning(Bucket=B, VersioningConfiguration={"Status": "Enabled"})
    hashes = {}
    for i, k in enumerate(keys()):
        s3.put_object(Bucket=B, Key=k, Body=body(i)); hashes[k] = hashlib.sha256(body(i)).hexdigest()
    STATE.write_text(json.dumps(hashes)); print(f"seeded {N} documents in s3://{B} (versioning enabled)")


def attack():
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(lambda k: s3.put_object(Bucket=B, Key=k, Body=os.urandom(2500)), keys()))
    print(f"encrypted {N} objects in {time.time() - t0:.1f}s ({N / (time.time() - t0):.0f} writes/s)")


def detect():
    with ThreadPoolExecutor(16) as ex:
        ent = list(ex.map(lambda k: entropy(s3.get_object(Bucket=B, Key=k, Range="bytes=0-2047")["Body"].read()), keys()))
    bad = sum(e > 7.5 for e in ent)
    print(f"{bad}/{N} objects have entropy > 7.5 bits/byte (plain text is ~4.5) -> {'ALERT: likely encryption' if bad > N * 0.1 else 'ok'}")
    return bad


def restore(k):
    vs = sorted(s3.list_object_versions(Bucket=B, Prefix=k).get("Versions", []), key=lambda v: v["LastModified"], reverse=True)
    for v in vs:
        if v["Key"] != k: continue
        data = s3.get_object(Bucket=B, Key=k, VersionId=v["VersionId"])["Body"].read()
        if entropy(data) < 7.5:
            if not v["IsLatest"]: s3.put_object(Bucket=B, Key=k, Body=data)
            return True
    return False


def recover():
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        ok = sum(ex.map(restore, keys()))
    print(f"restored {ok}/{N} objects from earlier versions in {time.time() - t0:.1f}s (RTO for this share)")


def verify():
    hashes = json.loads(STATE.read_text())
    good = sum(hashlib.sha256(s3.get_object(Bucket=B, Key=k)["Body"].read()).hexdigest() == h for k, h in hashes.items())
    print(f"{good}/{len(hashes)} objects match their seed hash"); return good == len(hashes)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("seed", "attack", "detect", "recover", "verify"): sys.exit(__doc__)
    r = globals()[cmd]()
    sys.exit(0 if r is not False else 1)
