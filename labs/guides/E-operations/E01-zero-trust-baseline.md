# E01 - Zero-trust security baseline

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (lab stack + kind) / DEMO (OneFS Simulator, ObjectScale) / HW (CSM Authorization on a real array) | 4 h | SEC, NET, STO, PLT | L01 `obs`, `ai` and `infra` profiles up; kind cluster from C04/C05; A02 for OneFS steps. |

Every endpoint of the AI Factory needs an identity, an encrypted channel and the least privilege that works. This lab scans the lab stack for gaps, closes the ones that can be closed in SIM, and writes the baseline the standard will require. The scanner is meant to report FAIL on the default lab stack: that list is your gap register. **Untested here:** OneFS RBAC/AD, ObjectScale IAM and CSM Authorization (no OneFS or ObjectScale on my VM); check the commands against your release.

## Steps

### Step 1 - [SIM] Scan the default stack
```bash
cd labs/env && PY=~/.venvs/aif/bin/python
$PY ops/zt_scan.py | tee ../evidence/e01-scan-before.txt
```
Expected on the default stack: S3 anonymous access and tenant isolation PASS; ports on all interfaces, plain HTTP, Trino/Elasticsearch/MLflow without authentication and Grafana anonymous admin FAIL. Each line names the questionnaire ID it is evidence for.

### Step 2 - [SIM] Apply the hardening overlay
```bash
export GRAFANA_ADMIN_PASSWORD="$(openssl rand -base64 18)"   # keep it in your password manager, not in Git
docker compose -f docker-compose.yml -f docker-compose.governance.yml -f docker-compose.hardened.yml \
  --profile obs --profile ai --profile infra up -d
$PY ops/zt_scan.py | tee ../evidence/e01-scan-after.txt
```
[docker-compose.hardened.yml](../../env/docker-compose.hardened.yml) binds every published port to `127.0.0.1` and disables anonymous Grafana. Expected: loopback and Grafana checks now PASS. TLS and Trino/Elasticsearch/MLflow authentication still FAIL: the overlay does not fix those, Steps 3-5 do.

### Step 3 - [SIM] TLS and authentication on the query engine
Trino only accepts passwords over HTTPS. Create a lab certificate and a password file:
```bash
mkdir -p trino/tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=localhost" \
  -keyout trino/tls/key.pem -out trino/tls/cert.pem && cat trino/tls/key.pem trino/tls/cert.pem > trino/tls/trino.pem
htpasswd -B -C 10 -c trino/tls/password.db analyst     # needs apache2-utils
```
Add to Trino `config.properties`: `http-server.https.enabled=true`, `http-server.https.port=8443`, `http-server.https.keystore.path=/etc/trino/tls/trino.pem`, `http-server.authentication.type=PASSWORD`, `internal-communication.shared-secret=<random>`; add `password-authenticator.properties` with `password-authenticator.name=file` and `file.password-file=/etc/trino/tls/password.db`. Mount `trino/tls` and recreate the container (`docker compose up -d --force-recreate trino`). Check: `curl -k -u analyst:<pw> https://localhost:8443/v1/info` works, a wrong password returns 401. Do not commit `trino/tls/`.

In production: certificates from the enterprise CA, Trino `OAUTH2` or `JWT` against the IdP (`SEC-01`), the Data Analytics Engine's own authentication settings, and Elasticsearch/Data Search Engine with `xpack.security.enabled=true` and TLS on HTTP and transport.

### Step 4 - [SIM] Kubernetes least privilege and default-deny
```bash
for t in team-a team-b; do
kubectl create ns $t --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n $t -f - <<Y
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: default-deny}
spec: {podSelector: {}, policyTypes: [Ingress, Egress]}
Y
kubectl create rolebinding $t-edit --clusterrole=edit --group=$t -n $t --dry-run=client -o yaml | kubectl apply -f -
done
kubectl auth can-i create pods -n team-b --as=alice --as-group=team-a     # expect: no
$PY ops/zt_scan.py | grep NET
```
kind's default CNI (kindnet) does not enforce NetworkPolicy; install Calico or Cilium in the cluster to see traffic actually blocked (`kubectl run` a client in team-a and `wget` a pod in team-b). Then add explicit allow policies for DNS and the S3/Trino endpoints.

### Step 5 - [SIM] Secrets and image provenance
- Secrets: the scan checks that no `.env`, key or kubeconfig file is tracked in Git. In Kubernetes, use External Secrets Operator against Vault (or the enterprise secret store) instead of `kubectl create secret` from a laptop.
- Images: pin by digest and sign. With [cosign](https://docs.sigstore.dev/): `cosign generate-key-pair`, `cosign sign --key cosign.key <registry>/<image>@sha256:...`, `cosign verify --key cosign.pub ...`; then enforce with a Kyverno or Sigstore policy-controller admission policy so unsigned images are rejected in `team-*` namespaces.

### Step 6 - [DEMO] OneFS RBAC and AD
On the OneFS Simulator: `isi auth ads create <domain> <admin>`; `isi auth roles create AIFactoryStorageOps --zone System`; `isi auth roles modify AIFactoryStorageOps --add-priv-read ISI_PRIV_SMARTQUOTAS --add-priv ISI_PRIV_SNAPSHOT --add-group <DOMAIN>\\storage-ops`. Disable `root` SSH for daily use, enable `isi audit settings global modify --protocol-auditing-enabled yes`, and confirm HTTPS-only PAPI with the enterprise certificate (`isi certificate server import`).

### Step 7 - [DEMO] S3 IAM least privilege
ObjectScale: create one IAM user or role per application, attach a policy limited to its bucket and prefix (`s3:GetObject`, `s3:PutObject` on `arn:aws:s3:::bu-finance/rag/*`), no `s3:*`. In SIM, Step 1 already proved tenant isolation with the finance key against `bu-research` (A09 created those identities).

### Step 8 - [HW] CSM Authorization
Install Dell CSM Authorization (proxy server + sidecar) for the PowerScale CSI driver, create a tenant and role with a storage quota, and bind the `team-a` namespace to it. Expected: a PVC bigger than the role quota is rejected by the proxy even though the Kubernetes ResourceQuota would allow it.

## Verify
- [ ] Before/after scans stored in `labs/evidence/`.
- [ ] Remaining FAIL lines each have a fix (Steps 3-5) or an approved exception.
- [ ] Cross-namespace access denied by RBAC; default-deny present in every `team-*` namespace.
- [ ] *(DEMO/HW)* OneFS roles mapped to AD groups; S3 policy scoped to a prefix; CSM Authorization quota enforced.

## Record for the standards
`SEC-01` identity provider for users and services. `SEC-02` access model (RBAC/ABAC). `SEC-04` TLS everywhere, including inside the cluster. `SEC-05` secrets manager. `SEC-08` image signing and admission. `SEC-09` privileged access to OneFS, iDRAC, Kubernetes. `NET-05` tenant segmentation. `STO-06` storage multi-tenancy model.

## Cleanup
`docker compose -f docker-compose.yml -f docker-compose.governance.yml --profile obs --profile ai --profile infra up -d` (back to the default bindings); `rm -rf trino/tls`; `kubectl delete ns team-a team-b` if C05 does not need them.
