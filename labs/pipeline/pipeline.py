#!/usr/bin/env python3
"""Deploy the orders pipeline (lab B08) to dev, QA or prod and promote the same Git commit through each.

  pipeline.py seed     --env dev [--inject-bad N]
  pipeline.py deploy   --env dev|qa|prod [--approved-by WHO]
  pipeline.py status
  pipeline.py rollback --env prod [--to SHA]
  pipeline.py destroy  --env dev|qa|prod      (lab cleanup)
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, string, subprocess, sys

import boto3, trino, yaml

HERE = pathlib.Path(__file__).resolve().parent
ENV_DIR = HERE.parent / "env"
CFG = yaml.safe_load((HERE / "environments.yaml").read_text())
DOTENV_FILE = ENV_DIR / ".env"   # lab only; CI sets the AIDP_* variables instead
DOTENV = dict(l.split("=", 1) for l in DOTENV_FILE.read_text().splitlines() if "=" in l and not l.startswith("#")) if DOTENV_FILE.exists() else {}
# Lab endpoints by default; CI runners in each environment override them.
TRINO = (os.environ.get("AIDP_TRINO_HOST", "localhost"), int(os.environ.get("AIDP_TRINO_PORT", "8080")))
S3_URL = os.environ.get("AIDP_S3_ENDPOINT", "http://localhost:8333")


def secret_for(account):
    # CI injects AIDP_SVC_<ENV>_SECRET from the secrets manager (SEC-05). SIM falls back to the lab identity file.
    if f"AIDP_{account.upper().replace('-', '_')}_SECRET" in os.environ:
        return os.environ[f"AIDP_{account.upper().replace('-', '_')}_SECRET"]
    ids = json.loads((ENV_DIR / "seaweedfs" / "s3.json").read_text())["identities"]
    return next(c["secretKey"] for i in ids if i["name"] == account for c in i["credentials"])


def s3():
    # Platform identity for buckets and release records: AIDP_S3_* in CI, the lab .env otherwise.
    env = lambda k, default=None: os.environ.get(f"AIDP_{k}", DOTENV.get(k, default))
    return boto3.client("s3", endpoint_url=S3_URL, region_name=env("S3_REGION", "us-east-1"),
                        aws_access_key_id=env("S3_ACCESS_KEY"), aws_secret_access_key=env("S3_SECRET_KEY"))


def ensure_buckets():
    c = s3()
    have = {b["Name"] for b in c.list_buckets()["Buckets"]}
    for b in [e["bucket"] for e in CFG["environments"].values()] + [CFG["releases_bucket"]]:
        if b not in have:
            c.create_bucket(Bucket=b)


def connect(user):
    return trino.dbapi.connect(host=TRINO[0], port=TRINO[1], user=user, catalog="iceberg").cursor()


def render(text, env):
    e = CFG["environments"][env]
    return string.Template(text).substitute(env=env, bucket=e["bucket"], **e["dq"])


def statements(text):
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def q(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def short(sha):
    return sha[:12] + ("-dirty" if sha.endswith("-dirty") else "")


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()


def apply_migrations(cur, env, sha):
    e = CFG["environments"][env]
    q(cur, f"CREATE SCHEMA IF NOT EXISTS {env}_meta WITH (location = 's3://{e['bucket']}/meta')")
    q(cur, f"CREATE TABLE IF NOT EXISTS {env}_meta.schema_migrations (version VARCHAR, checksum VARCHAR, git_sha VARCHAR, applied_at TIMESTAMP(6) WITH TIME ZONE)")
    applied = dict(q(cur, f"SELECT version, checksum FROM {env}_meta.schema_migrations"))
    new = []
    for f in sorted((HERE / "migrations").glob("V*.sql")):
        version, checksum = f.name.split("__")[0], hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        if version in applied:
            if applied[version] != checksum:
                sys.exit(f"migration {f.name} was changed after it was applied to {env}; add a new V### file instead")
            continue
        for s in statements(render(f.read_text(), env)):
            q(cur, s)
        q(cur, f"INSERT INTO {env}_meta.schema_migrations VALUES ('{version}', '{checksum}', '{sha}', current_timestamp)")
        new.append(f.name)
    print(f"migrations: {', '.join(new) if new else 'none pending'}")
    return new


def output_tables(cur, env):
    return [f"{s}.{t}" for s, t in q(cur, f"SELECT table_schema, table_name FROM information_schema.tables "
                                          f"WHERE table_schema IN ('{env}_curated', '{env}_consumption') ORDER BY 1, 2")]


def snapshots(cur, env):
    out = {}
    for t in output_tables(cur, env):
        s, n = t.split(".")
        rows = q(cur, f'SELECT snapshot_id FROM {s}."{n}$history" WHERE is_current_ancestor ORDER BY made_current_at DESC LIMIT 1')
        out[t] = rows[0][0] if rows else None
    return out


def restore(cur, snaps):
    for t, sid in snaps.items():
        if sid is None:
            q(cur, f"DELETE FROM {t}")
        else:
            q(cur, f"ALTER TABLE {t} EXECUTE rollback_to_snapshot({sid})")
        print(f"  restored {t} -> {sid if sid is not None else 'empty'}")


def run_spark(env):
    account = CFG["environments"][env]["service_account"]
    sql = "\n".join(render(f.read_text(), env) for f in sorted((HERE / "transforms").glob("*.sql")))
    cmd = [str(ENV_DIR / "bin" / "spark-sql"),
           "--conf", f"spark.sql.catalog.lake.s3.access-key-id={account}",
           "--conf", f"spark.sql.catalog.lake.s3.secret-access-key={secret_for(account)}",
           "-e", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:], file=sys.stderr)
    return r.returncode == 0


def releases(env):
    c, out = s3(), []
    for o in c.list_objects_v2(Bucket=CFG["releases_bucket"], Prefix=f"{env}/").get("Contents", []):
        out.append(json.loads(c.get_object(Bucket=CFG["releases_bucket"], Key=o["Key"])["Body"].read()))
    return sorted(out, key=lambda r: r["finished_at"])


def record(rel):
    rel["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")
    key = f"{rel['env']}/{rel['finished_at']}-{rel['git_sha'][:12]}.json"
    s3().put_object(Bucket=CFG["releases_bucket"], Key=key, Body=json.dumps(rel, indent=2).encode())
    print(f"release record: s3://{CFG['releases_bucket']}/{key}  status={rel['status']}")


def seed(args):
    env, e = args.env, CFG["environments"][args.env]
    ensure_buckets()
    apply_migrations(connect(e["service_account"]), env, git("rev-parse", "HEAD"))
    cur, raw = connect("admin"), f"{env}_raw.orders_events"   # ingestion runs as the platform identity
    if args.inject_bad:
        q(cur, f"INSERT INTO {raw} SELECT (SELECT max(order_id) FROM {raw}) + i, 1, -1.0, current_date, 'O', current_timestamp "
               f"FROM UNNEST(sequence(1, {args.inject_bad})) AS t(i)")
        print(f"{raw}: appended {args.inject_bad} rows with a negative amount")
        return
    cols = "order_id, customer_id, amount, order_date, status, current_timestamp"
    src = {"sample": f"SELECT {cols} FROM curated.orders WHERE order_id % 20 = 0",
           "masked": f"SELECT order_id, abs(from_big_endian_64(xxhash64(to_big_endian_64(customer_id)))) % 1000000, amount, order_date, status, current_timestamp FROM curated.orders",
           "full": f"SELECT {cols} FROM curated.orders"}[e["source"]]
    q(cur, f"DELETE FROM {raw}")
    q(cur, f"INSERT INTO {raw} {src}")
    if e["source"] == "sample":
        # late-arriving updates and a few bad rows so dev exercises dedup and quarantine
        q(cur, f"INSERT INTO {raw} SELECT order_id, customer_id, amount + 1, order_date, status, current_timestamp + INTERVAL '1' SECOND FROM {raw} WHERE order_id % 400 = 0")
        q(cur, f"INSERT INTO {raw} VALUES (-1, 1, -5.0, current_date, 'O', current_timestamp), (-2, 1, 10.0, current_date + INTERVAL '30' DAY, 'O', current_timestamp), (-3, 1, 10.0, current_date, 'X', current_timestamp)")
    print(f"{raw}: {q(cur, f'SELECT count(*) FROM {raw}')[0][0]} rows ({e['source']})")


def deploy(args):
    env, e = args.env, CFG["environments"][args.env]
    sha = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--", "."):
        if not e.get("allow_dirty"):
            sys.exit("REFUSED: uncommitted changes in labs/pipeline; only dev accepts uncommitted work. Commit and deploy the commit.")
        sha += "-dirty"
    prev = e.get("requires_passed_in")
    if prev and not any(r["git_sha"] == sha and r["status"] == "passed" for r in releases(prev)):
        sys.exit(f"REFUSED: commit {short(sha)} has no passed release in {prev}; promote through {prev} first.")
    if e.get("requires_approval"):
        authors = {git("log", "-1", "--format=%ae"), git("log", "-1", "--format=%an")}
        if not args.approved_by:
            sys.exit(f"REFUSED: {env} needs --approved-by (the reviewer who approved the release).")
        if args.approved_by in authors:
            sys.exit(f"REFUSED: {args.approved_by} wrote commit {short(sha)}; a different person must approve {env}.")
    ensure_buckets()
    rel = {"env": env, "git_sha": sha, "approved_by": args.approved_by, "pipeline": "orders",
           "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "service_account": e["service_account"]}
    print(f"deploying {short(sha)} to {env} as {e['service_account']}")
    cur = connect(e["service_account"])
    rel["migrations_applied"] = apply_migrations(cur, env, sha)
    rel["input_snapshot"] = snapshots_of(cur, f"{env}_raw.orders_events")
    rel["snapshots_before"] = snapshots(cur, env)
    rel["dq"] = {}
    try:
        ok = run_spark(env)
        print(f"transforms: {'ok' if ok else 'FAILED'}")
        if ok:
            for check, passed in q(cur, render((HERE / "dq.sql").read_text(), env)):
                rel["dq"][check] = passed
                print(f"  [{'PASS' if passed else 'FAIL'}] {check}")
            ok = bool(rel["dq"]) and all(rel["dq"].values())
    except Exception as e:  # an error after Spark committed must not leave unvalidated outputs live
        print(f"gate error: {e}", file=sys.stderr)
        rel["error"], ok = str(e)[:500], False
    if not ok:
        print(f"gate failed: restoring {env} outputs to their pre-deploy snapshots")
        restore(cur, rel["snapshots_before"])
        rel["status"] = "failed"
        record(rel)
        sys.exit(1)
    rel["snapshots_after"] = snapshots(cur, env)
    rel["rows"] = {t: q(cur, f"SELECT count(*) FROM {t}")[0][0] for t in rel["snapshots_after"]}
    rel["status"] = "passed"
    record(rel)


def snapshots_of(cur, table):
    s, n = table.split(".")
    rows = q(cur, f'SELECT snapshot_id FROM {s}."{n}$history" WHERE is_current_ancestor ORDER BY made_current_at DESC LIMIT 1')
    return rows[0][0] if rows else None


def status(_):
    print(f"{'env':5} {'commit':18} {'status':11} {'finished (UTC)':32} approved_by")
    for env in CFG["order"]:
        rs = releases(env)
        for r in rs[-3:]:
            print(f"{env:5} {short(r['git_sha']):18} {r['status']:11} {r['finished_at']:32} {r.get('approved_by') or '-'}")
        if not rs:
            print(f"{env:5} (never deployed)")


def rollback(args):
    env = args.env
    live = [r for r in releases(env) if r["status"] in ("passed", "rolled-back")]
    if not live:
        sys.exit(f"nothing deployed to {env}")
    current = live[-1]
    # After a rollback, "current" is an older release: only go further back from its original deploy time.
    cutoff = current.get("release_finished_at", current["finished_at"])
    targets = [r for r in live[:-1] if r["status"] == "passed" and r["git_sha"] != current["git_sha"]
               and (r["git_sha"].startswith(args.to) if args.to else r["finished_at"] < cutoff)]
    if not targets:
        sys.exit(f"no earlier passed release{' ' + args.to if args.to else ''} in {env} to roll back to")
    target = targets[-1]
    cur = connect(CFG["environments"][env]["service_account"])
    print(f"rolling {env} back from {short(current['git_sha'])} to {short(target['git_sha'])}")
    restore(cur, target["snapshots_after"])
    extra = set(snapshots(cur, env)) - set(target["snapshots_after"])
    for t in sorted(extra):
        print(f"  kept {t}: not part of {short(target['git_sha'])} (additive migration, unused by that release)")
    record({**target, "status": "rolled-back", "rolled_back_from": current["git_sha"], "approved_by": args.approved_by,
            "release_finished_at": target.get("release_finished_at", target["finished_at"])})


def destroy(args):
    env, cur = args.env, connect("admin")
    for schema in (f"{env}_raw", f"{env}_curated", f"{env}_consumption", f"{env}_meta"):
        if not q(cur, f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema}'"):
            continue
        for (t,) in q(cur, f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"):
            q(cur, f"DROP TABLE {schema}.{t}")
        q(cur, f"DROP SCHEMA {schema}")
    c = s3()
    for b, prefix in ((CFG["environments"][env]["bucket"], ""), (CFG["releases_bucket"], f"{env}/")):
        try:
            for page in c.get_paginator("list_objects_v2").paginate(Bucket=b, Prefix=prefix):
                for o in page.get("Contents", []):
                    c.delete_object(Bucket=b, Key=o["Key"])
        except c.exceptions.NoSuchBucket:
            pass
    print(f"{env}: tables, data and release records removed")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    envs = list(CFG["environments"])
    s = sub.add_parser("seed"); s.add_argument("--env", choices=envs, required=True); s.add_argument("--inject-bad", type=int, default=0)
    s.set_defaults(fn=seed)
    s = sub.add_parser("deploy"); s.add_argument("--env", choices=envs, required=True); s.add_argument("--approved-by")
    s.set_defaults(fn=deploy)
    sub.add_parser("status").set_defaults(fn=status)
    s = sub.add_parser("rollback"); s.add_argument("--env", choices=envs, required=True); s.add_argument("--to"); s.add_argument("--approved-by")
    s.set_defaults(fn=rollback)
    s = sub.add_parser("destroy"); s.add_argument("--env", choices=envs, required=True)
    s.set_defaults(fn=destroy)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
