"""Lab E01: zero-trust checklist scan of the running lab environment.

  python ops/zt_scan.py            # exit 1 if any check fails
Each check prints PASS / FAIL / SKIP with the evidence. The SIM stack is deliberately open (no TLS, no auth on most
engines); the point is to see what the scan catches, then apply docker-compose.hardened.yml and scan again.
"""
import json, pathlib, subprocess, sys, boto3, requests, botocore
from botocore import UNSIGNED
from botocore.config import Config

ENV = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.strip().split("=", 1) for l in open(ENV / ".env") if "=" in l and not l.startswith("#"))
ids = {i["name"]: i["credentials"][0] for i in json.load(open(ENV / "seaweedfs/s3.json"))["identities"]}
S3 = "http://localhost:8333"
results = []


def check(name, ctrl):
    def wrap(fn):
        try: status, ev = fn()
        except requests.ConnectionError: status, ev = "SKIP", "service not running"
        results.append((status, ctrl, name, ev))
    return wrap


def s3(user=None, unsigned=False):
    kw = {"config": Config(signature_version=UNSIGNED)} if unsigned else {
        "aws_access_key_id": ids[user]["accessKey"], "aws_secret_access_key": ids[user]["secretKey"]}
    return boto3.client("s3", endpoint_url=S3, region_name=env["S3_REGION"], **kw)


def denied(fn):
    try: fn(); return False
    except botocore.exceptions.ClientError: return True


@check("published ports bound to loopback only", "SEC-04 / NET")
def _():
    out = subprocess.run(["docker", "ps", "--filter", "label=com.docker.compose.project=aifactory-lab", "--format",
                          '{{.Label "com.docker.compose.service"}}\t{{.Ports}}'], capture_output=True, text=True).stdout  # all profiles
    wide = [l.split("\t")[0] for l in out.splitlines() if "0.0.0.0:" in l or "[::]:" in l]
    return ("FAIL", "listening on all interfaces: " + ", ".join(wide)) if wide else ("PASS", "all ports on 127.0.0.1")


@check("endpoints use TLS", "SEC-04")
def _():
    plain = [u for u in ("http://localhost:8333", "http://localhost:8080/v1/info", "http://localhost:9200", "http://localhost:5000/health")
             if requests.get(u, timeout=3).status_code < 500]
    return ("FAIL", "plain HTTP answers on " + ", ".join(plain)) if plain else ("PASS", "no plaintext endpoints")


@check("S3 rejects anonymous requests", "SEC-02")
def _():
    return ("PASS", "unsigned ListObjects denied") if denied(lambda: s3(unsigned=True).list_objects_v2(Bucket="bu-finance")) \
        else ("FAIL", "anonymous listing of bu-finance allowed")


@check("S3 tenant isolation (finance -> bu-research)", "SEC-02 / STO")
def _():
    c = s3("finance")
    read = denied(lambda: c.list_objects_v2(Bucket="bu-research"))
    write = denied(lambda: c.put_object(Bucket="bu-research", Key="zt-scan.txt", Body=b"x"))
    return ("PASS", "list and put denied") if read and write else ("FAIL", f"list denied={read} put denied={write}")


@check("Trino requires authentication", "SEC-01")
def _():
    r = requests.post("http://localhost:8080/v1/statement", data="SELECT 1", headers={"X-Trino-User": "mallory"}, timeout=5)
    return ("FAIL", "any user name is accepted without a password (user 'mallory')") if r.status_code == 200 else ("PASS", f"HTTP {r.status_code}")


@check("Elasticsearch requires authentication", "SEC-01")
def _():
    r = requests.get("http://localhost:9200/_cat/indices", timeout=5)
    return ("FAIL", "index list readable without credentials") if r.status_code == 200 else ("PASS", f"HTTP {r.status_code}")


@check("MLflow requires authentication", "SEC-01 / MLO-03")
def _():
    r = requests.get("http://localhost:5000/api/2.0/mlflow/registered-models/search", timeout=5)
    return ("FAIL", "model registry readable and writable without credentials") if r.status_code == 200 else ("PASS", f"HTTP {r.status_code}")


@check("Grafana has no anonymous admin", "SEC-02")
def _():
    r = requests.get("http://localhost:3000/api/org", timeout=5)
    return ("FAIL", "anonymous user has Admin on the org") if r.status_code == 200 else ("PASS", f"HTTP {r.status_code}")


@check("no secrets tracked in Git", "SEC-05")
def _():
    tracked = subprocess.run(["git", "ls-files", ".env", "*.pem", "*.key"], cwd=ENV, capture_output=True, text=True).stdout.split()
    return ("FAIL", "tracked: " + ", ".join(tracked)) if tracked else ("PASS", ".env and key files are untracked")


@check("Kubernetes team namespaces have a default-deny NetworkPolicy", "SEC-02 / NET")
def _():
    r = subprocess.run(["kubectl", "get", "networkpolicy", "-A", "-o", "json"], capture_output=True, text=True)
    if r.returncode: return "SKIP", "no kind cluster"
    nps = json.loads(r.stdout)["items"]
    ns = subprocess.run(["kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"], capture_output=True, text=True).stdout.split()
    teams = [n for n in ns if n.startswith("team-")]
    if not teams: return "SKIP", "no team-* namespaces (create them with C05)"
    missing = [n for n in teams if not any(p["metadata"]["namespace"] == n and p["spec"].get("podSelector") == {} for p in nps)]
    return ("FAIL", "no default-deny in " + ", ".join(missing)) if missing else ("PASS", "default-deny in " + ", ".join(teams))


if __name__ == "__main__":
    for st, ctrl, name, ev in results:
        print(f"{st:4}  {ctrl:15} {name:58} {ev}")
    n = {s: sum(r[0] == s for r in results) for s in ("PASS", "FAIL", "SKIP")}
    print(f"\n{n['PASS']} pass, {n['FAIL']} fail, {n['SKIP']} skip")
    sys.exit(1 if n["FAIL"] else 0)
