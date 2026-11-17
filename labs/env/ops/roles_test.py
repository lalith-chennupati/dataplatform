"""Lab E07: prove the Trino policy generated from architecture/roles.yaml grants and denies what the role model says.

  ~/.venvs/aif/bin/python ops/roles_test.py --setup   # as break-glass: create sample schemas and tables
  ~/.venvs/aif/bin/python ops/roles_test.py           # every persona x every table: SELECT, INSERT, PII masking
Needs Trino started with docker-compose.roles.yml. Expected access comes from roles.yaml, not from rules.json,
so a mistake in the generator shows up as a mismatch. Exit 1 on any mismatch.
"""
import argparse, pathlib, sys, time, requests

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import build_roles as R  # noqa: E402

TRINO = "http://localhost:8080"
ENVS, DOMAINS = R.ENVS, ["finance", "customer"]
LAYERS = {"dev": ["raw", "curated", "consumption"], "qa": ["curated", "consumption"], "prod": ["curated", "consumption"]}
MASKED = sorted({(m["product"].split(".")[0], m["layer"], m["product"].split(".")[1]) for m in R.SPEC["masks"]})


def sql(user, q):
    r = requests.post(f"{TRINO}/v1/statement", data=q, headers={"X-Trino-User": user}, timeout=30).json()
    rows = []
    while True:
        if "error" in r:
            raise PermissionError(r["error"]["message"])
        rows += r.get("data", [])
        if "nextUri" not in r:
            return rows
        r = requests.get(r["nextUri"], timeout=30).json()


def allowed(user, q):
    try:
        return True, sql(user, q)
    except PermissionError as e:
        if "Access Denied" in str(e):
            return False, str(e)
        raise


def setup():
    admin = next(p["user"] for p in R.SPEC["personas"] if "aidp-break-glass" in p["groups"])
    for env in ENVS:
        for d in DOMAINS:
            for layer in LAYERS[env]:
                s = f"iceberg.{env}_{d}_{layer}"
                sql(admin, f"CREATE SCHEMA IF NOT EXISTS {s} WITH (location = 's3://aidp-{env}/e07/{d}/{layer}')")
                sql(admin, f"CREATE TABLE IF NOT EXISTS {s}.t AS SELECT 1 AS id")
        for d, layer, table in MASKED:
            if layer in LAYERS[env]:
                sql(admin, f"CREATE TABLE IF NOT EXISTS iceberg.{env}_{d}_{layer}.{table} AS "
                           "SELECT 1 AS customer_id, 'Alice Smith' AS name, 'alice@example.com' AS email")
    print(f"setup done as {admin}")


def effective(persona):
    out = {"schemas": {}, "unmasked": set(), "all": False, "system": False}
    for g in persona["groups"]:
        x = R.expand(g)
        out["all"] |= x["all"]
        out["system"] |= x["system"]
        out["unmasked"] |= x["unmasked"]
        for s, a in x["schemas"].items():
            if R.STRENGTH[a] > R.STRENGTH.get(out["schemas"].get(s), 0):
                out["schemas"][s] = a
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true")
    args = ap.parse_args()
    if args.setup:
        return setup()
    t0, checks, bad = time.time(), 0, []

    def expect(user, what, want, got, detail=""):
        nonlocal checks
        checks += 1
        if want != got:
            bad.append(f"{user}: {what} expected {want}, got {got} {detail}"[:200])

    for p in R.SPEC["personas"]:
        u, e = p["user"], effective(p)
        summary = []
        for env in ENVS:
            for d in DOMAINS:
                for layer in LAYERS[env]:
                    s = f"{env}_{d}_{layer}"
                    access = "all" if e["all"] else e["schemas"].get(s)
                    ok_r, _ = allowed(u, f"SELECT count(*) FROM iceberg.{s}.t")
                    ok_w, _ = allowed(u, f"INSERT INTO iceberg.{s}.t VALUES (2)")
                    expect(u, f"SELECT {s}", access is not None, ok_r)
                    expect(u, f"INSERT {s}", access in ("all", "write", "owner"), ok_w)
                    if ok_r:
                        summary.append(f"{s}:{'RW' if ok_w else 'R'}")
            for d, layer, table in MASKED:
                s = f"{env}_{d}_{layer}"
                if layer not in LAYERS[env]:
                    continue
                clear = e["all"] or f"{env}_{d}" in e["unmasked"]
                want = "clear" if clear else "masked" if e["schemas"].get(s) else "denied"
                ok, rows = allowed(u, f"SELECT email FROM iceberg.{s}.{table} LIMIT 1")
                got = "denied" if not ok else "clear" if rows and "@" in rows[0][0] else "masked"
                expect(u, f"PII {s}.{table}", want, got)
                if ok:
                    summary.append(f"{s}.{table}:{got}")
        ok_sys, _ = allowed(u, "SELECT count(*) FROM system.runtime.nodes")
        expect(u, "system catalog", e["all"] or e["system"], ok_sys)
        print(f"{u:28} {' '.join(summary) or 'no data access'}{'  +system' if ok_sys else ''}")
    for b in bad:
        print("MISMATCH", b)
    print(f"{checks} checks, {len(bad)} mismatches, {time.time() - t0:.1f}s")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
