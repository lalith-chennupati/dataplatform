# E07 - Roles and privileges as code

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (lab Trino) / DEMO (Data Analytics Engine, ObjectScale, OneFS role mapping) | 2 h | SEC, LAK, DAT, PRV | L01 `core` profile up; B03 done (file-based access control); read [roles-and-privileges.md](../../../architecture/roles-and-privileges.md). |

The SRE team defines AIDP roles once, in [`roles.yaml`](../../../architecture/roles.yaml), and generates each component's policy from it. This lab validates the role model, generates the Trino policy, runs it on the lab Trino and proves every sample person can do exactly what the model says, nothing more. **Untested here:** mapping the roles to built-in roles in the Dell Data Analytics Engine (Starburst), ObjectScale and OneFS, because no Dell system was available; Step 6 lists what to check.

## Steps

### Step 1 - [SIM] Validate the role model
```bash
python3 tools/build_roles.py --check
```
Expected: `roles OK: 15 roles, 110 groups`. Then break it on purpose to see the guard rails. In `roles.yaml`, give `domain-engineer` `access: write` in `prod` and run `python3 tools/build_roles.py`. Expected: `domain-engineer: human role with write access in prod (only service accounts write to prod)`, and the same for `ml-engineer`, which inherits it. Undo the change. Then a separation-of-duties break: add `aidp-prod-customer-model-approver` to `mia-ml`'s groups (she is an `ml-engineer` in dev). Expected: `persona mia-ml: ml-engineer and model-approver together (a model builder must not approve their own model for prod)`. Undo.

### Step 2 - [SIM] Generate the policy
```bash
python3 tools/build_roles.py
git diff --stat
```
Writes [`roles-matrix.md`](../../../architecture/roles-matrix.md), diagram 11, and [`labs/env/trino/roles/rules.json`](../../env/trino/roles/rules.json) plus `group.txt`. Open `rules.json`: rules reference groups, never people; masked tables have one rule per group with access, the unmasked groups first; every section ends with a deny or execute-only rule.

### Step 3 - [SIM] Start Trino with the generated policy
```bash
cd labs/env
docker compose -f docker-compose.yml -f docker-compose.roles.yml --profile core up -d --force-recreate trino
until docker compose ps trino | grep -q healthy; do sleep 5; done
~/.venvs/aif/bin/python ops/roles_test.py --setup
```
[docker-compose.roles.yml](../../env/docker-compose.roles.yml) mounts the generated rules and a file group provider. `group.txt` stands in for AD / Keycloak groups. `--setup` runs as `admin` (in `aidp-break-glass`) and creates the sample schemas `iceberg.<env>_<domain>_<layer>` for finance and customer, plus `customer_master` with a name and email.

### Step 4 - [SIM] Prove allow and deny
```bash
~/.venvs/aif/bin/python ops/roles_test.py | tee ../evidence/e07-roles-test.txt
```
Expected: `320 checks, 0 mismatches`. Each line shows what a person can reach, for example:
- `fatima-finance` (finance reader): `prod_finance_consumption:R` only.
- `erik-fin-eng`: read/write in dev, read-only curated and consumption in prod.
- `sara-cust-steward`: `customer_master:masked`; `priya-cust-pii` (plus `pii-reader`): `customer_master:clear`.
- `olivia-sre` and `sam-auditor`: `no data access  +system` (they see the system catalog, not business data).
- `svc-prod-finance-pipeline`: the only identity with `RW` in prod.

The expected result comes from `roles.yaml`, so any `MISMATCH` line means the generator or the policy is wrong.

### Step 5 - [SIM] Change a role through review
Add `aidp-prod-finance-reader` to `sara-cust-steward` in `personas`, regenerate, and rerun Step 4 (Trino reloads the policy every 10 s). Expected: still `0 mismatches`, and Sara now also has `prod_finance_consumption:R`. In production this is an AD group change approved by the finance domain owner; the policy itself does not change. Revert afterwards.

### Step 6 - [DEMO] Map to Dell components (untested)
For each role in [roles-matrix.md](../../../architecture/roles-matrix.md), find the matching built-in role or policy in your Dell releases and write it in `roles.yaml` under `privileges`:
1. Data Analytics Engine (Starburst): built-in access control or the file / OPA policy generated here; group provider from LDAP or OIDC claims.
2. ObjectScale: IAM policies per bucket prefix for `svc-pipeline`; management roles (system admin, monitor) for `platform-*`.
3. PowerScale / OneFS: RBAC roles per access zone (for example audit, backup, security admin) for `platform-*` and `security-auditor`; file ACLs per domain path.
4. Data Search Engine: index privileges and document-level security per domain group.
5. iDRAC / OpenManage: AD groups through PAM for `platform-operator` and `platform-admin`.
Record each mapping as confirmed or still open.

## Verify
- [ ] `build_roles.py --check` passes, and both deliberate breaks were rejected.
- [ ] Generated policy runs on the lab Trino: `0 mismatches`.
- [ ] Masked PII is clear only for `pii-reader` and the pipeline service account.
- [ ] Platform and security roles have no business-data access.
- [ ] Only service accounts can write in prod.
- [ ] Dell role mappings written down, with open items listed.

## Record for the standards
`SEC-02` RBAC plus tag-based masking. `SEC-09` JIT admin and break-glass. `SEC-10` grant and denial events to the SIEM. `LAK-09` query-layer row and column control. `DAT-02` owners and stewards approve data access. `PRV-05` the test output as audit evidence. `ARC-03` group naming.

## Cleanup
```bash
docker compose --profile core up -d --force-recreate trino   # back to the default (open) Trino
```
The `iceberg.*_finance_*` and `*_customer_*` sample schemas can stay; drop them as `admin` if you need the space.
