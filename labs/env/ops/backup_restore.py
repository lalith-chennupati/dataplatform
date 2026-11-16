"""Lab E03 (SIM): back up the AI assets of the lab to a vault bucket and restore them.

  python ops/backup_restore.py backup                 # -> s3://vault/<timestamp>/ + manifest.json
  python ops/backup_restore.py list
  python ops/backup_restore.py restore <timestamp> [--only es,mlflow,catalog,checkpoints]
Assets: Elasticsearch index docs-chunks (mapping + documents incl. vectors), MLflow backend DB, Iceberg catalog DB,
checkpoints bucket. Iceberg data files in s3://warehouse are immutable and referenced by the catalog: production
protects them with bucket replication/object lock rather than copying them in every backup.
SIM stand-in for PowerProtect Data Manager / Velero; the restore order and checks are the part that carries over.
"""
import argparse, hashlib, io, json, os, pathlib, subprocess, sys, time, boto3
from elasticsearch import Elasticsearch, helpers

ENV = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.strip().split("=", 1) for l in open(ENV / ".env") if "=" in l and not l.startswith("#"))
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_URL", "http://localhost:8333"), region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])
ES = Elasticsearch(os.environ.get("ES_URL", "http://localhost:9200"))
VAULT, INDEX = "vault", "docs-chunks"
FILES = {"mlflow": ("mlflow", "/mlflow/mlflow.db"), "catalog": ("iceberg-rest", "/catalog/iceberg.db")}


def put(key, data):
    s3.put_object(Bucket=VAULT, Key=key, Body=data); return {"key": key, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def get(key):
    return s3.get_object(Bucket=VAULT, Key=key)["Body"].read()


def dcp(src, dst):
    subprocess.run(["docker", "compose", "cp", src, dst], cwd=ENV, check=True, capture_output=True)


def backup(a):
    ts, m, t0 = time.strftime("%Y%m%dT%H%M%S"), {}, time.time()
    try: s3.create_bucket(Bucket=VAULT)
    except s3.exceptions.ClientError: pass
    mapping = ES.indices.get_mapping(index=INDEX)[INDEX]["mappings"]
    docs = [{"_id": h["_id"], **h["_source"]} for h in helpers.scan(ES, index=INDEX, query={"query": {"match_all": {}}})]
    m["es"] = put(f"{ts}/es/{INDEX}.json", json.dumps({"mappings": mapping, "docs": docs}).encode()) | {"docs": len(docs)}
    for name, (svc, path) in FILES.items():
        tmp = ENV / "ops" / f".{name}.db"; dcp(f"{svc}:{path}", str(tmp))
        m[name] = put(f"{ts}/{name}/{pathlib.Path(path).name}", tmp.read_bytes()); tmp.unlink()
    objs = [o["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket="checkpoints") for o in p.get("Contents", [])]
    for k in objs:
        s3.copy_object(Bucket=VAULT, Key=f"{ts}/checkpoints/{k}", CopySource={"Bucket": "checkpoints", "Key": k})
    m["checkpoints"] = {"objects": len(objs)}
    put(f"{ts}/manifest.json", json.dumps(m, indent=1).encode())
    print(f"backup {ts}: {len(docs)} index docs, mlflow {m['mlflow']['bytes']} B, catalog {m['catalog']['bytes']} B, "
          f"{len(objs)} checkpoints in {time.time() - t0:.1f}s")


def list_(a):
    r = s3.list_objects_v2(Bucket=VAULT, Delimiter="/")
    for p in r.get("CommonPrefixes", []): print(p["Prefix"].rstrip("/"))


def restore(a):
    ts, only, t0 = a.ts, set(a.only.split(",")), time.time()
    m = json.loads(get(f"{ts}/manifest.json"))
    for name in ("es", *FILES):
        if name in only and hashlib.sha256(get(m[name]["key"])).hexdigest() != m[name]["sha256"]:
            sys.exit(f"{name}: checksum mismatch, backup {ts} is not trustworthy")
    if "es" in only:
        b = json.loads(get(m["es"]["key"]))
        ES.indices.delete(index=INDEX, ignore_unavailable=True); ES.indices.create(index=INDEX, mappings=b["mappings"])
        helpers.bulk(ES, ({"_index": INDEX, "_id": d.pop("_id"), "_source": d} for d in b["docs"]), refresh=True)
        print(f"es: restored {len(b['docs'])} docs into {INDEX}")
    for name, (svc, path) in FILES.items():
        if name in only:
            tmp = ENV / "ops" / f".{name}.db"; tmp.write_bytes(get(m[name]["key"]))
            dcp(str(tmp), f"{svc}:{path}"); tmp.unlink()
            subprocess.run(["docker", "compose", "restart", svc], cwd=ENV, check=True, capture_output=True)
            print(f"{name}: restored {path} and restarted {svc}")
    if "checkpoints" in only:
        pre = f"{ts}/checkpoints/"
        keys = [o["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=VAULT, Prefix=pre) for o in p.get("Contents", [])]
        for k in keys:
            s3.copy_object(Bucket="checkpoints", Key=k[len(pre):], CopySource={"Bucket": VAULT, "Key": k})
        print(f"checkpoints: restored {len(keys)} objects")
    print(f"restore of {ts} finished in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("backup").set_defaults(fn=backup); sp.add_parser("list").set_defaults(fn=list_)
    r = sp.add_parser("restore"); r.add_argument("ts"); r.add_argument("--only", default="es,mlflow,catalog,checkpoints"); r.set_defaults(fn=restore)
    a = ap.parse_args(); a.fn(a)
